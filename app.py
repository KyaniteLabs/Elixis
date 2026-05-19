"""Elixis — AI pattern synthesis for identity, brand, design, and naming.

Usage: python app.py [--port PORT]
"""

import hashlib
import hmac
import json
import os
import signal
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

from elixis.backup import (
    create_backup,
    list_backups,
    restore_backup,
    cleanup_old_backups,
    get_backup_status,
    auto_backup_if_enabled,
)
from elixis.engine import GameEngine
from elixis.logging_config import (
    clear_request_id,
    configure_root_logger,
    get_logger,
    set_request_id,
)
from elixis.naming import research_name
from elixis.quality import validate_output
from elixis.traces import save_run, log_request, get_diagnostics, get_recent_runs
from elixis.translate import (
    translate_text,
    translate_soulmd,
    get_supported_languages,
    detect_language,
    translate_text_stream,
    get_cache_stats,
    clear_cache,
)
from elixis.validation import (
    validate_brain_dump,
    get_content_security_policy,
)

PORT = 3110
ROOT_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(ROOT_DIR, "elixis", "templates")
STATIC_DIR = os.path.join(ROOT_DIR, "elixis", "static")
CSP_HEADER = get_content_security_policy()
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:3110")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
MAX_CONCURRENT_PIPELINES = int(os.environ.get("MAX_CONCURRENT_PIPELINES", "4"))
SSE_WRITE_TIMEOUT = int(os.environ.get("SSE_WRITE_TIMEOUT", "120"))
MAX_BODY_SIZE = int(os.environ.get("MAX_BODY_SIZE", str(2 * 1024 * 1024)))  # 2MB default
VALID_LENSES = {"identity", "brand", "design"}

logger = get_logger("elixis.server")

# Semaphore to prevent resource exhaustion from too many simultaneous LLM calls
_pipeline_semaphore = threading.Semaphore(MAX_CONCURRENT_PIPELINES)

# Graceful shutdown: track in-flight requests and drain on signal
_active_count = 0
_drain_condition = threading.Condition(threading.Lock())
_shutdown_requested = threading.Event()
SHUTDOWN_DRAIN_TIMEOUT = int(os.environ.get("SHUTDOWN_DRAIN_TIMEOUT", "30"))


def _request_enter():
    """Track a request entering processing. Returns False if shutting down."""
    if _shutdown_requested.is_set():
        return False
    with _drain_condition:
        global _active_count
        _active_count += 1
    return True


def _request_leave():
    """Track a request finishing processing."""
    with _drain_condition:
        global _active_count
        _active_count -= 1
        _drain_condition.notify_all()


def _get_brain_dump(data):
    """Return the primary synthesis text from accepted payload keys."""
    if not isinstance(data, dict):
        return ""
    if data.get("brain_dump") is not None:
        return data.get("brain_dump", "")
    return data.get("text", "")


def _validate_brain_dump_input(brain_dump):
    is_valid, error, meta = validate_brain_dump(brain_dump)
    return is_valid, error, meta.get("sanitized_text", brain_dump)


def _lens_error(lens):
    if lens in VALID_LENSES:
        return None
    return f"Invalid lens '{lens}'. Must be one of: {', '.join(sorted(VALID_LENSES))}"


def _llm_public_config():
    """Return model configuration safe to expose in per-run process traces."""
    from elixis.llm import cfg

    parsed = urlparse(cfg.base_url or "")
    host = parsed.netloc or parsed.path or ""
    return {
        "provider": cfg.provider,
        "model": cfg.default_model,
        "base_host": host,
        "classify_model": cfg.classify_model or cfg.default_model,
    }


def _process_trace_from_state(state, lens="identity"):
    """Build an auditable public trace for a pipeline run."""
    graph = state.metadata.get("pattern_graph", {})
    extraction = state.metadata.get("extraction_telemetry", {})
    enrichment = state.metadata.get("enrichment_telemetry", {})
    pattern_telemetry = state.metadata.get("pattern_telemetry", {})
    classification = pattern_telemetry.get("llm_classification", {})
    timings = state.timings or {}

    entities = []
    for bead in state.beads:
        data = bead.to_dict()
        entities.append({
            "name": data.get("canonical") or data.get("name"),
            "type": data.get("type"),
            "themes": data.get("themes", [])[:8],
            "traits": data.get("traits", [])[:6],
            "domains": data.get("domains", [])[:5],
            "confidence": data.get("confidence"),
            "provenance": data.get("provenance"),
        })

    return {
        "visibility": (
            "Auditable process trace. Internal token-level reasoning is not exposed; "
            "this shows the observable extraction, scoring, evidence, timings, and model metadata."
        ),
        "lens": lens,
        "model": _llm_public_config(),
        "phases": [
            {
                "name": "declaration",
                "method": "LLM entity extraction with heuristic fallback",
                "duration_ms": timings.get("declaration_ms"),
                "source": extraction.get("source"),
                "entity_count": extraction.get("entity_count", len(entities)),
                "model": extraction.get("model"),
                "provider": extraction.get("provider"),
                "tokens_in": extraction.get("tokens_in"),
                "tokens_out": extraction.get("tokens_out"),
            },
            {
                "name": "elaboration",
                "method": "External/curated enrichment plus knowledge-base cross-reference",
                "duration_ms": timings.get("elaboration_ms"),
                "source": enrichment.get("source") or "research+knowledge_base",
            },
            {
                "name": "connection",
                "method": "Pattern graph: LLM classification blended with keyword/type/knowledge scoring",
                "duration_ms": timings.get("connection_ms"),
                "source": "llm+rules" if pattern_telemetry.get("llm_available") else "rules",
                "pattern_count": pattern_telemetry.get("pattern_count", len(graph.get("patterns", []))),
                "bridge_count": pattern_telemetry.get("bridge_count", len(graph.get("bridges", []))),
                "model": classification.get("model"),
                "provider": classification.get("provider"),
                "tokens_in": classification.get("tokens_in"),
                "tokens_out": classification.get("tokens_out"),
            },
            {
                "name": "resolution",
                "method": f"{lens} lens document generation",
                "duration_ms": timings.get("resolution_ms") or timings.get("stage3_synthesis_ms"),
            },
        ],
        "pattern_matching": {
            "method": "0.7 LLM classification + 0.3 keyword/theme/type/knowledge scoring",
            "llm_available": pattern_telemetry.get("llm_available"),
            "classification_source": classification.get("source"),
            "classification_error": classification.get("error"),
            "top_patterns": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "probability": p.get("probability"),
                    "supporting_entities": p.get("supporting_entities"),
                    "sub_patterns": p.get("sub_patterns", [])[:3],
                }
                for p in graph.get("patterns", [])[:8]
            ],
            "bridges": graph.get("bridges", [])[:5],
            "entity_scores": graph.get("entity_scores", [])[:8],
            "analysis_notes": graph.get("analysis_notes", [])[:6],
            "emergent_topic": graph.get("emergent_topic"),
            "emergent_theme": graph.get("emergent_theme"),
            "consensus_score": graph.get("consensus_score"),
        },
        "entities": entities,
        "timings_ms": timings,
    }


def run_pipeline(brain_dump):
    """Run the full pipeline on a brain dump string using the GameEngine."""
    if not brain_dump or len(brain_dump.strip()) < 3:
        return {"error": "Brain dump is empty or too short"}

    engine = GameEngine()
    try:
        output = engine.run_full(brain_dump, lens="identity")
    except RuntimeError as e:
        return {"error": str(e)}

    state = engine.state
    graph = state.metadata.get("pattern_graph", {})

    save_run(brain_dump,
             [b.to_dict() for b in state.beads],
             graph, output,
             stage_timings=state.timings)

    return {
        "stage1_entities": [b.to_dict() for b in state.beads],
        "stage2_graph": graph,
        "output": output,
        "stage3_output": output,
        "stage3_soulmd": output,
        "timings": state.timings,
        "process_trace": _process_trace_from_state(state, lens="identity"),
    }


def run_game_pipeline(brain_dump, lens="identity"):
    """Run the full pattern synthesis pipeline using the GameEngine."""
    if not brain_dump or len(brain_dump.strip()) < 3:
        return {"error": "Brain dump is empty or too short"}

    if lens not in VALID_LENSES:
        return {"error": f"Invalid lens '{lens}'. Must be one of: {', '.join(sorted(VALID_LENSES))}"}

    engine = GameEngine()
    try:
        output = engine.run_full(brain_dump, lens=lens)
    except RuntimeError as e:
        return {"error": str(e)}

    state = engine.state
    return {
        "lens": lens,
        "stage1_entities": [b.to_dict() for b in state.beads],
        "stage2_graph": state.metadata.get("pattern_graph", {}),
        "output": output,
        "stage3_output": output,
        "stage3_soulmd": output if lens == "identity" else None,
        "threads": [t.to_dict() for t in state.threads],
        "tensions": state.tensions,
        "timings": state.timings,
        "quality": validate_output(output, lens=lens),
        "process_trace": _process_trace_from_state(state, lens=lens),
    }


class Handler(BaseHTTPRequestHandler):

    def _request_id(self):
        if not hasattr(self, '_req_id'):
            self._req_id = uuid.uuid4().hex[:12]
        set_request_id(self._req_id)
        return self._req_id

    def finish(self):
        try:
            super().finish()
        finally:
            if (
                hasattr(self, "_request_start")
                and hasattr(self, "_response_status")
                and not getattr(self, "_response_logged", False)
                and hasattr(self, "command")
                and hasattr(self, "path")
            ):
                self._log(self.command, self._route_path(), self._response_status, self._request_start)
            clear_request_id()

    def send_response(self, code, message=None):
        self._response_status = code
        return super().send_response(code, message)

    def _route_path(self):
        return urlparse(self.path).path

    def do_GET(self):
        start = time.time()
        self._request_start = start
        self._request_id()
        path = self._route_path()
        if path in ("", "/"):
            self._serve_file("landing.html", "text/html")
            self._log("GET", path, 200, start)
        elif path == "/api/diagnostics":
            if not self._require_admin():
                self._log("GET", path, self._admin_response_status_for_log(), start)
                return
            self._json_response(get_diagnostics())
            self._log("GET", path, 200, start)
        elif path == "/api/health":
            llm_ok = False
            health_errors = {}
            try:
                from elixis.llm import is_available as llm_available
                llm_ok = llm_available()
                if not llm_ok:
                    health_errors["llm"] = "LLM inference unavailable"
            except Exception as e:
                health_errors["llm"] = str(e)
            disk_ok = True
            try:
                if hasattr(os, 'statvfs'):
                    stat = os.statvfs(os.path.dirname(os.path.abspath(__file__)))
                    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
                    disk_ok = free_gb > 0.5
                    if not disk_ok:
                        health_errors["disk"] = f"Low disk space: {free_gb:.2f}GB free"
            except Exception as e:
                health_errors["disk"] = str(e)
            status = "ok" if (llm_ok and disk_ok) else "degraded"
            payload = {
                "status": status,
                "llm": "available" if llm_ok else "unavailable",
                "disk": "ok" if disk_ok else "low",
            }
            if health_errors:
                payload["errors"] = health_errors
            self._json_response(payload)
            self._log("GET", path, 200, start)
        elif path == "/api/runs":
            if not self._require_admin():
                self._log("GET", path, self._admin_response_status_for_log(), start)
                return
            self._json_response({"runs": get_recent_runs(50)})
            self._log("GET", path, 200, start)
        elif path == "/api/languages":
            self._json_response({"languages": get_supported_languages()})
            self._log("GET", path, 200, start)
        elif path == "/api/translation-cache":
            self._json_response(get_cache_stats())
            self._log("GET", path, 200, start)
        elif path == "/api/backups":
            if not self._require_admin():
                self._log("GET", path, self._admin_response_status_for_log(), start)
                return
            self._json_response({"backups": list_backups()})
            self._log("GET", path, 200, start)
        elif path == "/api/backups/status":
            if not self._require_admin():
                self._log("GET", path, self._admin_response_status_for_log(), start)
                return
            self._json_response(get_backup_status())
            self._log("GET", path, 200, start)
        elif path == "/api/lenses":
            self._json_response({"lenses": sorted(VALID_LENSES)})
            self._log("GET", path, 200, start)
        elif path == "/api/game/schema":
            from elixis.bead import VALID_TYPES
            self._json_response({
                "phases": ["declaration", "elaboration", "connection", "resolution"],
                "lenses": sorted(VALID_LENSES),
                "entity_types": sorted(VALID_TYPES),
            })
            self._log("GET", path, 200, start)
        elif path == "/robots.txt":
            self._serve_robots(start)
        elif path == "/sitemap.xml":
            self._serve_sitemap(start)
        elif path == "/llms.txt":
            status = self._serve_file(
                os.path.join(ROOT_DIR, "llms.txt"),
                "text/plain; charset=utf-8",
                cache_max_age=3600,
            )
            self._log("GET", path, status, start)
        elif path == "/llms-full.txt":
            status = self._serve_file(
                os.path.join(ROOT_DIR, "llms-full.txt"),
                "text/plain; charset=utf-8",
                cache_max_age=3600,
            )
            self._log("GET", path, status, start)
        else:
            status = self._serve_static(path)
            self._log("GET", path, status, start)

    def do_POST(self):
        start = time.time()
        self._request_start = start
        self._request_id()
        path = self._route_path()
        if path == "/api/extract":
            self._handle_extract(start)
        elif path == "/api/extract/stream":
            self._handle_extract(start, force_stream=True)
        elif path == "/api/translate":
            self._handle_translate(start)
        elif path == "/api/detect-language":
            self._handle_detect_language(start)
        elif path in ("/api/translate-stream", "/api/translate/stream"):
            self._handle_translate_stream(start)
        elif path == "/api/naming":
            self._handle_naming(start)
        elif path == "/api/backups":
            if not self._require_admin():
                self._log("POST", path, self._admin_response_status_for_log(), start)
                return
            self._handle_backup_create(start)
        elif path == "/api/backups/restore":
            if not self._require_admin():
                self._log("POST", path, self._admin_response_status_for_log(), start)
                return
            self._handle_backup_restore(start)
        elif path == "/api/backups/cleanup":
            if not self._require_admin():
                self._log("POST", path, self._admin_response_status_for_log(), start)
                return
            self._handle_backup_cleanup(start)
        elif path == "/api/game":
            self._handle_game(start)
        elif path == "/api/game/stream":
            self._handle_game_stream(start)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self._log("POST", path, 404, start)

    def do_DELETE(self):
        start = time.time()
        self._request_start = start
        self._request_id()
        path = self._route_path()
        if path == "/api/translation-cache":
            if not self._require_admin():
                self._log("DELETE", path, self._admin_response_status_for_log(), start)
                return
            result = clear_cache()
            self._json_response(result)
            self._log("DELETE", path, 200, start)
        elif path.startswith("/api/backups/"):
            if not self._require_admin():
                self._log("DELETE", path, self._admin_response_status_for_log(), start)
                return
            name = path[len("/api/backups/"):]
            # Validate name to prevent path traversal
            import re as _re
            if not name or not _re.match(r'^[a-zA-Z0-9_-]+$', name):
                self._json_response({"removed": 0, "error": "Invalid backup name"}, 400)
                return
            result = {"removed": 0, "error": None}
            backups = list_backups()
            target = next((b for b in backups if b["name"] == name), None)
            if target:
                try:
                    os.remove(target["path"])
                    result = {"removed": 1, "name": name}
                except OSError as e:
                    result = {"removed": 0, "error": str(e)}
            else:
                result = {"removed": 0, "error": f"Backup not found: {name}"}
            self._json_response(result)
            self._log("DELETE", path, 200, start)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self._log("DELETE", path, 404, start)

    # --- Endpoint handlers ---

    def _read_json_body(self):
        """Read and parse JSON body, returning (data, error_response)."""
        try:
            length = max(0, int(self.headers.get("Content-Length", 0)))
            if length > MAX_BODY_SIZE:
                return None, {
                    "error": f"Request body too large. Maximum {MAX_BODY_SIZE} bytes allowed.",
                    "_status": 413,
                }
            body = self.rfile.read(length).decode("utf-8")
            return json.loads(body), None
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, {"error": f"Invalid request body: {e}"}

    def _json_body_error(self, err):
        status = err.pop("_status", 400)
        self._json_response(err, status)

    def _is_head(self):
        return self.command == "HEAD"

    def _admin_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[len("Bearer "):].strip()
        return self.headers.get("X-Admin-API-Key", "")

    def _require_admin(self):
        if not ADMIN_API_KEY:
            self._admin_response_status = 503
            self._json_response({"error": "Admin API key is not configured"}, 503)
            return False
        if hmac.compare_digest(self._admin_token(), ADMIN_API_KEY):
            self._admin_response_status = 200
            return True
        self._admin_response_status = 401
        self._json_response({"error": "Admin authorization required"}, 401)
        return False

    def _admin_response_status_for_log(self):
        return getattr(self, "_admin_response_status", 401)

    def _handle_extract(self, start, force_stream=False):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return
        brain_dump = _get_brain_dump(data)

        is_valid, error, brain_dump = _validate_brain_dump_input(brain_dump)
        if not is_valid:
            self._json_response({"error": error}, 400)
            return

        accept = self.headers.get("Accept", "")
        if force_stream or "text/event-stream" in accept or data.get("stream"):
            if not _request_enter():
                self._json_response({"error": "Server is shutting down"}, 503)
                return
            if not _pipeline_semaphore.acquire(blocking=False):
                _request_leave()
                self._json_response({"error": "Server busy — too many concurrent pipeline requests"}, 503)
                return
            try:
                self._handle_stream(brain_dump, start)
            finally:
                _pipeline_semaphore.release()
                _request_leave()
        else:
            if not _request_enter():
                self._json_response({"error": "Server is shutting down"}, 503)
                return
            if not _pipeline_semaphore.acquire(blocking=False):
                _request_leave()
                self._json_response({"error": "Server busy — too many concurrent pipeline requests"}, 503)
                return
            try:
                result = run_pipeline(brain_dump)
            finally:
                _pipeline_semaphore.release()
                _request_leave()
            status = 200 if "error" not in result else 500
            self._json_response(result, status)
            self._log("POST", self.path, status, start, extra={
                "entity_count": len(result.get("stage1_entities", [])),
                "emergent": result.get("stage2_graph", {}).get("emergent_topic"),
                "soulmd_length": len(result.get("stage3_soulmd", "")),
                "timings": result.get("timings"),
            })

    def _handle_translate(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        text = data.get("text", "")
        target_lang = data.get("target_lang", "")
        source_lang = data.get("source_lang", "en")

        if not text:
            self._json_response({"error": "No text provided"}, 400)
            return
        if not target_lang:
            self._json_response({"error": "No target_lang provided"}, 400)
            return

        is_soulmd = data.get("soulmd", False)
        if is_soulmd:
            result = translate_soulmd(text, target_lang)
        else:
            result = translate_text(text, target_lang, source_lang)

        status = 200 if result.get("success") else 500
        self._json_response(result, status)
        self._log("POST", self.path, status, start, extra={
            "target_lang": target_lang,
            "source_lang": source_lang,
            "text_length": len(text),
            "success": result.get("success"),
        })

    def _handle_detect_language(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        text = data.get("text", "")
        if not text:
            self._json_response({"error": "No text provided"}, 400)
            return
        if len(text.strip()) < 10:
            self._json_response({"error": "Text too short for reliable language detection"}, 400)
            return
        try:
            from elixis.llm import is_available as llm_available
            if not llm_available():
                self._json_response({"error": "Language detection unavailable: LLM inference unavailable"}, 503)
                return
        except Exception as e:
            self._json_response({"error": f"Language detection unavailable: {e}"}, 503)
            return

        detected = detect_language(text)
        if not detected:
            self._json_response({"error": "Could not detect language"}, 422)
            return
        self._json_response({
            "detected_language": detected,
            "language_name": get_supported_languages().get(detected, "Unknown") if detected else None,
        })
        self._log("POST", self.path, 200, start)

    def _handle_translate_stream(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        text = data.get("text", "")
        target_lang = data.get("target_lang", "")
        source_lang = data.get("source_lang", "en")

        if not text:
            self._json_response({"error": "No text provided"}, 400)
            return
        if not target_lang:
            self._json_response({"error": "No target_lang provided"}, 400)
            return

        if not _request_enter():
            self._json_response({"error": "Server is shutting down"}, 503)
            return
        try:
            self._begin_sse_response()

            rid = self._request_id()
            deadline = time.time() + SSE_WRITE_TIMEOUT
            try:
                for event in translate_text_stream(text, target_lang, source_lang):
                    if time.time() > deadline:
                        break
                    if isinstance(event, dict):
                        event["request_id"] = rid
                    payload = json.dumps(event)
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                    deadline = time.time() + SSE_WRITE_TIMEOUT
            except (BrokenPipeError, ConnectionResetError):
                logger.warning(f"[{rid}] Client disconnected during translation stream")

            self._log("POST", self.path, 200, start, extra={
                "target_lang": target_lang,
                "source_lang": source_lang,
                "text_length": len(text),
            })
        finally:
            _request_leave()

    def _handle_naming(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        name = data.get("name", "")
        context = data.get("context", "")
        generate_variants = data.get("generate_variants", True)

        if not name:
            self._json_response({"error": "No name provided"}, 400)
            return

        report = research_name(name, context, generate_variants)
        self._json_response(report)
        self._log("POST", self.path, 200, start, extra={
            "name": name,
            "context": context,
            "variant_count": len(report.get("variants", [])),
        })

    def _handle_backup_create(self, start):
        result = create_backup()
        status = 200 if result["status"] == "success" else 202 if result["status"] == "skipped" else 500
        self._json_response(result, status)
        self._log("POST", self.path, status, start, extra={"backup_status": result["status"]})

    def _handle_backup_restore(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        backup_name = data.get("name", "")
        force = data.get("force", False)

        if not backup_name:
            self._json_response({"error": "No backup name provided"}, 400)
            return

        result = restore_backup(backup_name, force=force)
        status = 200 if result["success"] else 400
        self._json_response(result, status)
        self._log("POST", self.path, status, start, extra={"backup_name": backup_name})

    def _handle_backup_cleanup(self, start):
        result = cleanup_old_backups()
        self._json_response(result)
        self._log("POST", self.path, 200, start)

    def _handle_game(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        brain_dump = _get_brain_dump(data)
        lens = data.get("lens", "identity")
        lens_error = _lens_error(lens)
        if lens_error:
            self._json_response({"error": lens_error}, 400)
            return

        is_valid, error, brain_dump = _validate_brain_dump_input(brain_dump)
        if not is_valid:
            self._json_response({"error": error}, 400)
            return

        if not _request_enter():
            self._json_response({"error": "Server is shutting down"}, 503)
            return
        if not _pipeline_semaphore.acquire(blocking=False):
            _request_leave()
            self._json_response({"error": "Server busy"}, 503)
            return
        try:
            result = run_game_pipeline(brain_dump, lens=lens)
        finally:
            _pipeline_semaphore.release()
            _request_leave()

        status = 200 if "error" not in result else 500
        self._json_response(result, status)
        self._log("POST", self.path, status, start, extra={
            "lens": lens,
            "entity_count": len(result.get("stage1_entities", [])),
            "output_length": len(result.get("stage3_output", "")),
            "timings": result.get("timings"),
        })

    def _handle_game_stream(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_body_error(err)
            return

        brain_dump = _get_brain_dump(data)
        lens = data.get("lens", "identity")
        lens_error = _lens_error(lens)
        if lens_error:
            self._json_response({"error": lens_error}, 400)
            return

        is_valid, error, brain_dump = _validate_brain_dump_input(brain_dump)
        if not is_valid:
            self._json_response({"error": error}, 400)
            return

        if not _request_enter():
            self._json_response({"error": "Server is shutting down"}, 503)
            return
        if not _pipeline_semaphore.acquire(blocking=False):
            _request_leave()
            self._json_response({"error": "Server busy"}, 503)
            return

        try:
            self._begin_sse_response()

            rid = self._request_id()
            deadline = time.time() + SSE_WRITE_TIMEOUT

            engine = GameEngine()
            timings = {}

            def _send(event):
                if isinstance(event, dict):
                    event["request_id"] = rid
                payload = json.dumps(event)
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()

            try:
                # Phase 1: Declaration
                t0 = time.time()
                state = engine.declare_themes(brain_dump)
                timings["declaration_ms"] = int((time.time() - t0) * 1000)
                _send({"type": "entities", "data": [b.to_dict() for b in state.beads]})

                # Phase 2: Elaboration
                t0 = time.time()
                engine.elaborate()
                timings["elaboration_ms"] = int((time.time() - t0) * 1000)

                # Phase 3: Connection
                t0 = time.time()
                engine.connect_domains()
                timings["connection_ms"] = int((time.time() - t0) * 1000)
                _send({"type": "graph", "data": state.metadata.get("pattern_graph", {})})
                if state.tensions:
                    _send({"type": "tensions", "data": state.tensions})
                _send({"type": "process_trace", "data": _process_trace_from_state(state, lens=lens)})

                # Phase 4: Resolution (streamed)
                for event in engine.resolve_stream(lens=lens, stage_timings=timings):
                    if time.time() > deadline:
                        break
                    _send(event)
                    deadline = time.time() + SSE_WRITE_TIMEOUT

            except (BrokenPipeError, ConnectionResetError):
                logger.warning(f"[{rid}] Client disconnected during game stream")

            self._log("POST", self.path, 200, start, extra={
                "streamed": True, "lens": lens, "timings": timings,
            })
        finally:
            _pipeline_semaphore.release()
            _request_leave()

    # --- Streaming ---

    def _handle_stream(self, brain_dump, start):
        timings = {}
        rid = self._request_id()

        self._begin_sse_response()

        def _send(event):
            if isinstance(event, dict):
                event["request_id"] = rid
            payload = json.dumps(event)
            self.wfile.write(f"data: {payload}\n\n".encode())
            self.wfile.flush()

        deadline = time.time() + SSE_WRITE_TIMEOUT
        state = None
        graph = {}

        try:
            engine = GameEngine()

            # Phase 1: Declaration
            t0 = time.time()
            state = engine.declare_themes(brain_dump)
            timings["stage1_extract_ms"] = int((time.time() - t0) * 1000)

            # Phase 1b: Elaboration
            t0 = time.time()
            engine.elaborate()
            timings["stage1b_research_ms"] = int((time.time() - t0) * 1000)

            _send({"type": "entities", "data": [b.to_dict() for b in state.beads]})

            # Phase 2: Connection
            t0 = time.time()
            engine.connect_domains()
            timings["stage2_graph_ms"] = int((time.time() - t0) * 1000)

            graph = state.metadata.get("pattern_graph", {})
            _send({"type": "graph", "data": graph})
            _send({"type": "process_trace", "data": _process_trace_from_state(state, lens="identity")})

            # Phase 3: Stream resolution
            for event in engine.resolve_stream(lens="identity", stage_timings=timings):
                if time.time() > deadline:
                    logger.warning(f"[{rid}] SSE write timeout exceeded")
                    break
                _send(event)
                deadline = time.time() + SSE_WRITE_TIMEOUT

            save_run(brain_dump,
                     [b.to_dict() for b in state.beads],
                     graph, "",
                     stage_timings=timings)

        except (BrokenPipeError, ConnectionResetError):
            logger.warning(f"[{rid}] Client disconnected during SSE stream")

        self._log("POST", "/api/extract", 200, start, extra={
            "streamed": True,
            "entity_count": len(state.beads) if state else 0,
            "emergent": graph.get("emergent_topic") if graph else None,
            "timings": timings,
        })

    # --- Response helpers ---

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, X-Admin-API-Key")
        self.send_header("X-Request-ID", self._request_id())

    def _begin_sse_response(self):
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self._send_cors_headers()
        self.end_headers()

    def _json_response(self, data, status=200):
        if isinstance(data, dict):
            data["_request_id"] = self._request_id()
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self._send_cors_headers()
        self.end_headers()
        if not self._is_head():
            self.wfile.write(body)

    def _log(self, method, path, status, start, extra=None):
        self._response_logged = True
        duration_ms = (time.time() - start) * 1000
        rid = self._request_id()
        if extra is None:
            extra = {}
        extra["request_id"] = rid
        log_request(method, path, status, duration_ms, extra)
        logger.info(f"[{rid}] {method} {path} {status} {duration_ms:.0f}ms")

    def _serve_file(self, filename, content_type, cache_max_age=0):
        filepath = filename if os.path.isabs(filename) else os.path.join(TEMPLATE_DIR, filename)
        if not os.path.isfile(filepath):
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            return 404
        with open(filepath, "rb") as f:
            content = f.read()

        # Check ETag before sending response headers
        if cache_max_age > 0:
            etag = '"' + hashlib.md5(content).hexdigest()[:16] + '"'
            if_none_match = self.headers.get("If-None-Match")
            if if_none_match and if_none_match == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self._send_cors_headers()
                self.end_headers()
                return 304

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if cache_max_age > 0:
            self.send_header("Cache-Control", f"public, max-age={cache_max_age}")
            self.send_header("ETag", etag)
        self._send_cors_headers()
        self.end_headers()
        if not self._is_head():
            self.wfile.write(content)
        return 200

    # Cache TTL by content type (seconds)
    _CACHE_TTL = {
        ".css": 86400, ".js": 86400, ".png": 604800, ".jpg": 604800,
        ".svg": 604800, ".ico": 604800, ".webp": 604800,
        ".woff2": 2592000, ".woff": 2592000, ".webmanifest": 3600,
        ".html": 0, ".json": 0,
    }

    def _serve_static(self, path):
        prefix = "/static/"
        if not path.startswith(prefix):
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            return 404
        filename = path[len(prefix):]
        resolved = os.path.realpath(os.path.join(STATIC_DIR, filename))
        static_root = os.path.realpath(STATIC_DIR)
        if not (resolved == static_root or resolved.startswith(static_root + os.sep)):
            self.send_response(403)
            self._send_cors_headers()
            self.end_headers()
            return 403
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".html": "text/html",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".json": "application/json",
            ".webp": "image/webp",
            ".woff2": "font/woff2",
            ".woff": "font/woff",
            ".webmanifest": "application/manifest+json",
        }
        _DENIED_EXTENSIONS = {".py", ".env", ".cfg", ".ini", ".sh", ".bak", ".log", ".db", ".sqlite"}
        ext = os.path.splitext(filename)[1].lower()
        if ext in _DENIED_EXTENSIONS:
            self.send_response(403)
            self._send_cors_headers()
            self.end_headers()
            return 403
        content_type = content_types.get(ext)
        if content_type is None:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            return 404
        cache_ttl = self._CACHE_TTL.get(ext, 0)
        return self._serve_file(resolved, content_type, cache_max_age=cache_ttl)

    def _serve_robots(self, start):
        host = self.headers.get("Host", f"localhost:{PORT}")
        proto = "https" if os.environ.get("HTTPS") else "http"
        base_url = f"{proto}://{host}"
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            f"Sitemap: {base_url}/sitemap.xml\n"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self._send_cors_headers()
        self.end_headers()
        if not self._is_head():
            self.wfile.write(body)
        self._log("GET", "/robots.txt", 200, start)

    def _serve_sitemap(self, start):
        host = self.headers.get("Host", f"localhost:{PORT}")
        proto = "https" if os.environ.get("HTTPS") else "http"
        base_url = f"{proto}://{host}"
        now = time.strftime("%Y-%m-%d")
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{base_url}/</loc><lastmod>{now}</lastmod>"
            "<changefreq>weekly</changefreq><priority>1.0</priority></url>\n"
            f"  <url><loc>{base_url}/llms.txt</loc><lastmod>{now}</lastmod>"
            "<changefreq>weekly</changefreq><priority>0.7</priority></url>\n"
            "</urlset>\n"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self._send_cors_headers()
        self.end_headers()
        if not self._is_head():
            self.wfile.write(body)
        self._log("GET", "/sitemap.xml", 200, start)

    def do_OPTIONS(self):
        self._request_start = time.time()
        self._request_id()
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    configure_root_logger()
    port = PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    server = ThreadedHTTPServer(("0.0.0.0", port), Handler)

    shutdown_event = threading.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        _shutdown_requested.set()
        shutdown_event.set()
        server.shutdown()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info(f"Elixis running on http://localhost:{port} (PID: {os.getpid()})")

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Drain in-flight requests
        drain_start = time.time()
        with _drain_condition:
            remaining = _active_count
        if remaining > 0:
            logger.info(f"Waiting for {remaining} in-flight requests to complete (max {SHUTDOWN_DRAIN_TIMEOUT}s)...")
            while time.time() - drain_start < SHUTDOWN_DRAIN_TIMEOUT:
                with _drain_condition:
                    if _active_count <= 0:
                        break
                    remaining_ms = max(0, (SHUTDOWN_DRAIN_TIMEOUT - (time.time() - drain_start)) * 1000)
                    _drain_condition.wait(timeout=min(remaining_ms / 1000, 1.0))
            with _drain_condition:
                final = _active_count
            if final > 0:
                logger.warning(f"Drain timeout exceeded, {final} requests still active")
            else:
                logger.info("All in-flight requests completed")
        auto_backup_if_enabled()
        server.server_close()
        server_thread.join(timeout=5)
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
