"""Soulcraft — The Glass Bead Game for AI Personas.

Usage: python app.py [--port PORT]
"""

import json
import os
import signal
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from soulcraft.backup import (
    create_backup,
    list_backups,
    restore_backup,
    cleanup_old_backups,
    get_backup_status,
    auto_backup_if_enabled,
)
from soulcraft.entities import extract_entities
from soulcraft.logging_config import get_logger, configure_root_logger
from soulcraft.naming import research_name, format_research_report
from soulcraft.patterns import build_pattern_graph
from soulcraft.research import enrich_entities
from soulcraft.synthesis import synthesize_soulmd, synthesize_soulmd_stream
from soulcraft.traces import save_run, log_request, get_diagnostics, get_recent_runs
from soulcraft.translate import (
    translate_text,
    translate_soulmd,
    get_supported_languages,
    detect_language,
    translate_text_stream,
    get_cache_stats,
    clear_cache,
)
from soulcraft.validation import (
    validate_brain_dump,
    validate_api_request,
    get_content_security_policy,
)

PORT = 3110
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "soulcraft", "templates")
CSP_HEADER = get_content_security_policy()
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:3110")
MAX_CONCURRENT_PIPELINES = int(os.environ.get("MAX_CONCURRENT_PIPELINES", "4"))
SSE_WRITE_TIMEOUT = int(os.environ.get("SSE_WRITE_TIMEOUT", "120"))
MAX_BODY_SIZE = int(os.environ.get("MAX_BODY_SIZE", str(2 * 1024 * 1024)))  # 2MB default

logger = get_logger("soulcraft.server")

# Semaphore to prevent resource exhaustion from too many simultaneous LLM calls
_pipeline_semaphore = threading.Semaphore(MAX_CONCURRENT_PIPELINES)

# Graceful shutdown: track in-flight requests and drain on signal
_active_requests = threading.Semaphore(0)  # count of in-flight requests
_active_count = 0
_active_count_lock = threading.Lock()
_shutdown_requested = threading.Event()
SHUTDOWN_DRAIN_TIMEOUT = int(os.environ.get("SHUTDOWN_DRAIN_TIMEOUT", "30"))


def _request_enter():
    """Track a request entering processing. Returns False if shutting down."""
    if _shutdown_requested.is_set():
        return False
    with _active_count_lock:
        global _active_count
        _active_count += 1
    return True


def _request_leave():
    """Track a request finishing processing."""
    with _active_count_lock:
        global _active_count
        _active_count -= 1
    # If shutdown is waiting, pulse the event
    if _shutdown_requested.is_set():
        _shutdown_requested.set()


def run_pipeline(brain_dump):
    """Run the full 3-stage pipeline on a brain dump string."""
    if not brain_dump or len(brain_dump.strip()) < 3:
        return {"error": "Brain dump is empty or too short"}

    timings = {}

    try:
        t0 = time.time()
        entities = extract_entities(brain_dump)
        timings["stage1_extract_ms"] = int((time.time() - t0) * 1000)
    except RuntimeError as e:
        return {"error": str(e)}

    t0 = time.time()
    enrich_entities(entities)
    timings["stage1b_research_ms"] = int((time.time() - t0) * 1000)

    t0 = time.time()
    graph = build_pattern_graph(entities, brain_dump)
    timings["stage2_graph_ms"] = int((time.time() - t0) * 1000)

    t0 = time.time()
    soulmd = synthesize_soulmd(entities, graph)
    timings["stage3_synthesis_ms"] = int((time.time() - t0) * 1000)

    save_run(brain_dump, entities, graph, soulmd, stage_timings=timings)

    return {
        "stage1_entities": entities,
        "stage2_graph": graph,
        "stage3_soulmd": soulmd,
        "timings": timings,
    }


class Handler(BaseHTTPRequestHandler):

    def _request_id(self):
        if not hasattr(self, '_req_id'):
            self._req_id = uuid.uuid4().hex[:12]
        return self._req_id

    def do_GET(self):
        start = time.time()
        self._request_id()
        if self.path in ("", "/"):
            self._serve_file("landing.html", "text/html")
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/diagnostics":
            self._json_response(get_diagnostics())
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/health":
            llm_ok = False
            try:
                from soulcraft.llm import is_available as llm_available
                llm_ok = llm_available()
            except Exception:
                pass
            disk_ok = True
            try:
                if hasattr(os, 'statvfs'):
                    stat = os.statvfs(os.path.dirname(os.path.abspath(__file__)))
                    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
                    disk_ok = free_gb > 0.5
            except Exception:
                pass
            status = "ok" if (llm_ok and disk_ok) else "degraded"
            self._json_response({
                "status": status,
                "llm": "available" if llm_ok else "unavailable",
                "disk": "ok" if disk_ok else "low",
            })
        elif self.path == "/api/runs":
            self._json_response({"runs": get_recent_runs(50)})
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/languages":
            self._json_response({"languages": get_supported_languages()})
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/translation-cache":
            self._json_response(get_cache_stats())
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/backups":
            self._json_response({"backups": list_backups()})
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/backups/status":
            self._json_response(get_backup_status())
            self._log("GET", self.path, 200, start)
        else:
            self._serve_static(self.path)
            self._log("GET", self.path, 200, start)

    def do_POST(self):
        start = time.time()
        self._request_id()
        if self.path == "/api/extract":
            self._handle_extract(start)
        elif self.path == "/api/translate":
            self._handle_translate(start)
        elif self.path == "/api/detect-language":
            self._handle_detect_language(start)
        elif self.path == "/api/translate-stream":
            self._handle_translate_stream(start)
        elif self.path == "/api/naming":
            self._handle_naming(start)
        elif self.path == "/api/backups":
            self._handle_backup_create(start)
        elif self.path == "/api/backups/restore":
            self._handle_backup_restore(start)
        elif self.path == "/api/backups/cleanup":
            self._handle_backup_cleanup(start)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self._log("POST", self.path, 404, start)

    def do_DELETE(self):
        start = time.time()
        self._request_id()
        if self.path == "/api/translation-cache":
            result = clear_cache()
            self._json_response(result)
            self._log("DELETE", self.path, 200, start)
        elif self.path.startswith("/api/backups/"):
            name = self.path[len("/api/backups/"):]
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
            self._log("DELETE", self.path, 200, start)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self._log("DELETE", self.path, 404, start)

    # --- Endpoint handlers ---

    def _read_json_body(self):
        """Read and parse JSON body, returning (data, error_response)."""
        try:
            length = max(0, min(int(self.headers.get("Content-Length", 0)), MAX_BODY_SIZE))
            body = self.rfile.read(length).decode("utf-8")
            return json.loads(body), None
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, {"error": f"Invalid request body: {e}"}

    def _handle_extract(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_response(err, 400)
            return
        brain_dump = data.get("brain_dump", "")

        is_valid, error, _ = validate_brain_dump(brain_dump)
        if not is_valid:
            self._json_response({"error": error}, 400)
            return

        accept = self.headers.get("Accept", "")
        if "text/event-stream" in accept or data.get("stream"):
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
            self._json_response(err, 400)
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
            self._json_response(err, 400)
            return

        text = data.get("text", "")
        if not text:
            self._json_response({"error": "No text provided"}, 400)
            return

        detected = detect_language(text)
        self._json_response({
            "detected_language": detected,
            "language_name": get_supported_languages().get(detected, "Unknown") if detected else None,
        })
        self._log("POST", self.path, 200, start)

    def _handle_translate_stream(self, start):
        data, err = self._read_json_body()
        if err:
            self._json_response(err, 400)
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
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Content-Security-Policy", CSP_HEADER)
            self._send_cors_headers()
            self.end_headers()

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
                pass

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
            self._json_response(err, 400)
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
            self._json_response(err, 400)
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

    # --- Streaming ---

    def _handle_stream(self, brain_dump, start):
        timings = {}
        rid = self._request_id()

        try:
            t0 = time.time()
            entities = extract_entities(brain_dump)
            timings["stage1_extract_ms"] = int((time.time() - t0) * 1000)
        except RuntimeError as e:
            self._json_response({"error": str(e)}, 503)
            self._log("POST", "/api/extract", 503, start, extra={"error": str(e)})
            return

        t0 = time.time()
        enrich_entities(entities)
        timings["stage1b_research_ms"] = int((time.time() - t0) * 1000)

        t0 = time.time()
        graph = build_pattern_graph(entities, brain_dump)
        timings["stage2_graph_ms"] = int((time.time() - t0) * 1000)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Content-Security-Policy", CSP_HEADER)
        self._send_cors_headers()
        self.end_headers()

        deadline = time.time() + SSE_WRITE_TIMEOUT
        try:
            for event in synthesize_soulmd_stream(entities, graph, stage_timings=timings):
                if time.time() > deadline:
                    logger.warning(f"[{rid}] SSE write timeout exceeded, aborting stream")
                    break
                if isinstance(event, dict):
                    event["request_id"] = rid
                payload = json.dumps(event)
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                deadline = time.time() + SSE_WRITE_TIMEOUT
        except (BrokenPipeError, ConnectionResetError):
            logger.warning(f"[{rid}] Client disconnected during SSE stream")

        self._log("POST", "/api/extract", 200, start, extra={
            "streamed": True,
            "entity_count": len(entities),
            "emergent": graph.get("emergent_topic"),
            "timings": timings,
        })

    # --- Response helpers ---

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("X-Request-ID", self._request_id())

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
        self.wfile.write(body)

    def _log(self, method, path, status, start, extra=None):
        duration_ms = (time.time() - start) * 1000
        rid = self._request_id()
        if extra is None:
            extra = {}
        extra["request_id"] = rid
        log_request(method, path, status, duration_ms, extra)
        logger.info(f"[{rid}] {method} {path} {status} {duration_ms:.0f}ms")

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(TEMPLATE_DIR, filename)
        if not os.path.isfile(filepath):
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _serve_static(self, path):
        filename = path.lstrip("/")
        resolved = os.path.realpath(os.path.join(TEMPLATE_DIR, filename))
        if not resolved.startswith(os.path.realpath(TEMPLATE_DIR)):
            self.send_response(403)
            self._send_cors_headers()
            self.end_headers()
            return
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".html": "text/html",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        _, ext = os.path.splitext(filename)
        content_type = content_types.get(ext, "application/octet-stream")
        self._serve_file(filename, content_type)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

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

    logger.info(f"Soulcraft running on http://localhost:{port} (PID: {os.getpid()})")

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
        with _active_count_lock:
            remaining = _active_count
        if remaining > 0:
            logger.info(f"Waiting for {remaining} in-flight requests to complete (max {SHUTDOWN_DRAIN_TIMEOUT}s)...")
            while time.time() - drain_start < SHUTDOWN_DRAIN_TIMEOUT:
                with _active_count_lock:
                    if _active_count <= 0:
                        break
                time.sleep(0.5)
            with _active_count_lock:
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
