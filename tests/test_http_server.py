"""HTTP server handler tests for app.py.

Tests the Handler class directly using mocked I/O streams,
without starting a real HTTP server.
"""

import io
import json
import unittest
from unittest.mock import patch, MagicMock, ANY

from app import Handler, _shutdown_requested, run_game_pipeline, run_pipeline


class _FakeSocket:
    """Minimal socket-like object for testing BaseHTTPRequestHandler."""

    def __init__(self, response_bytes):
        self._response = response_bytes

    def makefile(self, mode, *args, **kwargs):
        if "r" in mode:
            return io.BytesIO(self._response)
        return io.BytesIO()

    def sendall(self, data):
        pass

    def close(self):
        pass

    def getpeername(self):
        return ("127.0.0.1", 12345)


def _make_handler(method, path, body=None, headers=None):
    """Create a Handler with a fake socket for testing."""
    request_line = f"{method} {path} HTTP/1.1\r\n"
    header_lines = ""
    if headers:
        for k, v in headers.items():
            header_lines += f"{k}: {v}\r\n"

    body_bytes = b""
    if body is not None:
        body_bytes = json.dumps(body).encode()
        header_lines += f"Content-Length: {len(body_bytes)}\r\n"

    raw = (request_line + header_lines + "\r\n").encode() + body_bytes
    fake_socket = _FakeSocket(raw)
    fake_server = MagicMock()

    handler = Handler.__new__(Handler)
    handler.request = fake_socket
    handler.client_address = ("127.0.0.1", 12345)
    handler.server = fake_server
    handler._headers_buffer = []
    handler._headers_sent = False
    handler.request_version = "HTTP/1.1"
    handler.command = method
    handler.path = path
    handler.rfile = io.BytesIO(body_bytes)
    handler.wfile = io.BytesIO()
    handler.requestline = f"{method} {path} HTTP/1.1"

    # Parse headers into a dict-like object
    handler.headers = {}
    if headers:
        handler.headers = headers
    if body is not None and "Content-Length" not in (headers or {}):
        handler.headers["Content-Length"] = str(len(body_bytes))

    return handler


class TestGetRoutes(unittest.TestCase):
    """Test GET endpoint routing and response structure."""

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_log')
    @patch('app.get_diagnostics')
    @patch('app.ADMIN_API_KEY', 'test-key')
    def test_diagnostics_endpoint(self, mock_diag, mock_log, mock_header, mock_end, mock_cors, mock_resp):
        mock_diag.return_value = {"status": "ok", "total_runs": 0}
        handler = _make_handler("GET", "/api/diagnostics", headers={"Authorization": "Bearer test-key"})
        handler._json_response = MagicMock()

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        handler._json_response.assert_called_once()
        data = handler._json_response.call_args[0][0]
        self.assertEqual(data["status"], "ok")

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.get_supported_languages')
    def test_languages_endpoint(self, mock_langs, mock_log, mock_json):
        mock_langs.return_value = {"en": "English", "es": "Spanish"}
        handler = _make_handler("GET", "/api/languages")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("languages", data)
        self.assertIn("en", data["languages"])

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_game_schema_documents_connection_thread_outputs(self, mock_log, mock_json):
        handler = _make_handler("GET", "/api/game/schema")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        data = mock_json.call_args[0][0]
        self.assertIn("threads", data["connection_outputs"])
        self.assertIn("cross_domain_thread_count", data["connection_outputs"])

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.get_supported_languages')
    def test_route_matching_ignores_query_string(self, mock_langs, mock_log, mock_json):
        mock_langs.return_value = {"en": "English"}
        handler = _make_handler("GET", "/api/languages?source=operator")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_json.assert_called_once()
        self.assertIn("languages", mock_json.call_args[0][0])
        mock_log.assert_called_with("GET", "/api/languages", 200, ANY)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.get_cache_stats')
    def test_translation_cache_endpoint(self, mock_stats, mock_log, mock_json):
        mock_stats.return_value = {"entries": 5, "size_bytes": 1024}
        handler = _make_handler("GET", "/api/translation-cache")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertEqual(data["entries"], 5)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.list_backups')
    @patch('app.ADMIN_API_KEY', 'test-key')
    def test_backups_endpoint(self, mock_list, mock_log, mock_json):
        mock_list.return_value = [{"name": "backup_1", "size_bytes": 100}]
        handler = _make_handler("GET", "/api/backups", headers={"X-Admin-API-Key": "test-key"})

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("backups", data)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_protected_endpoint_requires_admin_key(self, mock_log, mock_json):
        handler = _make_handler("GET", "/api/diagnostics")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_json.assert_called_once()
        data, status = mock_json.call_args[0]
        self.assertEqual(status, 503)
        self.assertIn("Admin API key", data["error"])

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('elixis.llm.is_available', return_value=False)
    def test_health_reports_degraded_reason(self, mock_available, mock_log, mock_json):
        handler = _make_handler("GET", "/api/health")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("errors", payload)
        self.assertIn("llm", payload["errors"])

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    @patch.object(Handler, '_log')
    def test_landing_page_reflects_broader_synthesis_scope(self, mock_log, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("GET", "/")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        body = handler.wfile.getvalue().decode("utf-8")
        legacy_scope = " ".join(("Glass", "Bead", "Game"))
        self.assertNotIn(legacy_scope, body)
        self.assertIn("identity, brand voice, design systems, naming research", body)
        self.assertIn('id="about"', body)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    def test_static_social_preview_asset_is_served(self, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("GET", "/static/og-image.svg")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_resp.assert_called_with(200)
        body = handler.wfile.getvalue().decode("utf-8")
        self.assertIn("<svg", body)
        self.assertIn("Elixis", body)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    @patch.object(Handler, '_log')
    def test_llms_txt_is_served_for_ai_crawlers(self, mock_log, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("GET", "/llms.txt")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_resp.assert_called_with(200)
        body = handler.wfile.getvalue().decode("utf-8")
        self.assertIn("AI pattern synthesis engine", body)
        mock_log.assert_called_with("GET", "/llms.txt", 200, ANY)


class TestPostValidation(unittest.TestCase):
    """Test POST endpoint input validation."""

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_extract_empty_body(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/extract", body={"brain_dump": ""})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        # Should get a 400 for invalid brain dump
        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("error", data)
        status = mock_json.call_args[0][1] if len(mock_json.call_args[0]) > 1 else mock_json.call_args[1].get("status", 200)
        self.assertEqual(status, 400)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_translate_no_text(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/translate", body={"target_lang": "es"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("error", data)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_translate_no_target_lang(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/translate", body={"text": "Hello"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("error", data)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('elixis.llm.is_available', return_value=False)
    def test_detect_language_reports_llm_unavailable(self, mock_available, mock_log, mock_json):
        handler = _make_handler("POST", "/api/detect-language", body={"text": "Bonjour le monde complet"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        data, status = mock_json.call_args[0]
        self.assertEqual(status, 503)
        self.assertIn("unavailable", data["error"])

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_naming_no_name(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/naming", body={})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("error", data)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    def test_ingest_requires_exactly_one_source_target(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/ingest", body={})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        data, status = mock_json.call_args[0]
        self.assertEqual(status, 400)
        self.assertIn("Source Target", data["error"])

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch("elixis.ingest.ingest_source", return_value={"run_id": "abc", "source_corpus": {"signal_count": 2}})
    def test_ingest_endpoint_returns_shared_ingestion_result(self, mock_ingest, mock_log, mock_json):
        handler = _make_handler("POST", "/api/ingest", body={"path": ".", "include_code": True})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_ingest.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertEqual(data["run_id"], "abc")
        self.assertEqual(data["source_corpus"]["signal_count"], 2)

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch("elixis.market.create_market_kit", return_value={"run_id": "kit", "market_kit": {"title": "Kit"}})
    def test_market_kit_endpoint_uses_orchestration(self, mock_market, mock_log, mock_json):
        handler = _make_handler("POST", "/api/market-kit", body={"github": "https://github.com/KyaniteLabs/Elixis"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_market.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertEqual(data["market_kit"]["title"], "Kit")

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.MAX_BODY_SIZE', 16)
    def test_rejects_oversized_json_body(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/extract", body={"brain_dump": "x" * 100})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        data, status = mock_json.call_args[0]
        self.assertEqual(status, 413)
        self.assertIn("too large", data["error"])

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    @patch.object(Handler, '_log')
    def test_post_404(self, mock_log, mock_end, mock_cors, mock_resp):
        handler = _make_handler("POST", "/api/nonexistent", body={})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_resp.assert_called_with(404)

    @patch.object(Handler, '_handle_stream')
    @patch.object(Handler, '_log')
    def test_extract_stream_slash_alias_forces_sse(self, mock_log, mock_stream):
        handler = _make_handler("POST", "/api/extract/stream", body={"text": "Batman and Athena"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_stream.assert_called_once()

    @patch.object(Handler, '_handle_translate_stream')
    @patch.object(Handler, '_log')
    def test_translate_stream_slash_alias_routes(self, mock_log, mock_stream):
        handler = _make_handler("POST", "/api/translate/stream", body={"text": "Hello", "target_lang": "en"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_stream.assert_called_once()


class TestCorsHeaders(unittest.TestCase):
    """Test CORS and security headers."""

    @patch.object(Handler, 'send_header')
    def test_cors_headers_present(self, mock_header):
        handler = _make_handler("GET", "/")
        handler._send_cors_headers()

        headers_sent = {call[0][0]: call[0][1] for call in mock_header.call_args_list}
        self.assertIn("Access-Control-Allow-Origin", headers_sent)
        self.assertIn("Access-Control-Allow-Methods", headers_sent)
        self.assertIn("Authorization", headers_sent["Access-Control-Allow-Headers"])
        self.assertIn("X-Request-ID", headers_sent)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    def test_head_json_response_writes_no_body(self, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("HEAD", "/api/health")

        handler._json_response({"status": "ok"})

        self.assertEqual(handler.wfile.getvalue(), b"")

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    def test_sse_response_closes_finite_stream(self, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("POST", "/api/game/stream")

        handler._begin_sse_response()

        headers_sent = {call[0][0]: call[0][1] for call in mock_header.call_args_list}
        self.assertEqual(headers_sent["Connection"], "close")
        self.assertTrue(handler.close_connection)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    def test_options_returns_204(self, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("OPTIONS", "/api/extract")

        with patch.object(Handler, 'do_OPTIONS', Handler.do_OPTIONS):
            handler.do_OPTIONS()

        mock_resp.assert_called_with(204)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    @patch.object(Handler, '_log')
    def test_unknown_static_route_logs_404(self, mock_log, mock_end, mock_cors, mock_resp):
        handler = _make_handler("GET", "/missing")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_resp.assert_called_with(404)
        mock_log.assert_called_with("GET", "/missing", 404, ANY)


class TestRequestId(unittest.TestCase):
    """Test request ID generation and propagation."""

    def test_request_id_is_12_chars(self):
        handler = _make_handler("GET", "/")
        rid = handler._request_id()
        self.assertEqual(len(rid), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in rid))

    def test_request_id_stable_per_handler(self):
        handler = _make_handler("GET", "/")
        rid1 = handler._request_id()
        rid2 = handler._request_id()
        self.assertEqual(rid1, rid2)


class TestShutdownGuard(unittest.TestCase):
    """Test that new requests are rejected during shutdown."""

    def setUp(self):
        _shutdown_requested.clear()

    def tearDown(self):
        _shutdown_requested.clear()

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.validate_brain_dump')
    def test_rejects_during_shutdown(self, mock_validate, mock_log, mock_json):
        mock_validate.return_value = (True, None, {})
        _shutdown_requested.set()

        handler = _make_handler("POST", "/api/extract", body={"brain_dump": "Batman"})
        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("shutting down", data.get("error", "").lower())


class TestGamePayloads(unittest.TestCase):
    """Test game endpoint payload compatibility and validation."""

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.run_game_pipeline')
    def test_game_accepts_text_alias(self, mock_pipeline, mock_log, mock_json):
        mock_pipeline.return_value = {"stage1_entities": [], "output": "ok", "stage3_output": "ok"}
        handler = _make_handler("POST", "/api/game", body={"text": "Batman and Athena", "lens": "brand"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_pipeline.assert_called_once()
        self.assertEqual(mock_pipeline.call_args[0][0], "Batman and Athena")
        self.assertEqual(mock_pipeline.call_args.kwargs["lens"], "brand")
        mock_json.assert_called_once()

    @patch.object(Handler, '_json_response')
    @patch.object(Handler, '_log')
    @patch('app.run_game_pipeline')
    def test_game_rejects_invalid_lens_as_client_error(self, mock_pipeline, mock_log, mock_json):
        handler = _make_handler("POST", "/api/game", body={"brain_dump": "Batman and Athena", "lens": "unknown"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_pipeline.assert_not_called()
        data, status = mock_json.call_args[0]
        self.assertEqual(status, 400)
        self.assertIn("Invalid lens", data["error"])

    @patch.object(Handler, '_log')
    def test_finish_logs_early_validation_errors(self, mock_log):
        handler = _make_handler("POST", "/api/game", body={"brain_dump": "Batman and Athena", "lens": "unknown"})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()
        self.assertFalse(mock_log.called)

        handler.finish()

        mock_log.assert_called_once_with("POST", "/api/game", 400, ANY)

    def test_legacy_pipeline_includes_normalized_output_alias(self):
        class FakeBead:
            def to_dict(self):
                return {
                    "canonical": "Athena",
                    "type": "mythological",
                    "themes": ["wisdom", "strategy"],
                    "traits": ["strategic clarity"],
                    "confidence": 0.92,
                }

        class FakeThread:
            def to_dict(self):
                return {
                    "bead_a": "Athena",
                    "bead_b": "Batman",
                    "relationship": "complements",
                    "strength": 0.8,
                    "isomorphic": True,
                    "domains_bridged": ["spirituality", "literature"],
                    "evidence": ["Shared themes: strategy"],
                }

        class FakeEngine:
            def __init__(self):
                self.state = MagicMock()
                self.state.beads = [FakeBead()]
                self.state.threads = [FakeThread()]
                self.state.metadata = {
                    "pattern_graph": {
                        "patterns": [
                            {
                                "id": "wisdom",
                                "name": "Wisdom & Knowledge",
                                "probability": 0.88,
                                "supporting_entities": 1,
                                "sub_patterns": ["strategy"],
                            }
                        ],
                        "bridges": [],
                        "threads": [FakeThread().to_dict()],
                        "thread_count": 1,
                        "cross_domain_thread_count": 1,
                    },
                    "pattern_telemetry": {
                        "llm_available": True,
                        "llm_classification": {
                            "source": "llm",
                            "provider": "anthropic",
                            "model": "glm-5.1",
                        },
                    },
                }
                self.state.timings = {"declaration_ms": 12, "connection_ms": 34}

            def run_full(self, brain_dump, lens="identity"):
                return "# SOUL.md"

        model_config = {
            "provider": "anthropic",
            "model": "glm-5.1",
            "base_host": "api.z.ai",
            "classify_model": "glm-5.1",
        }
        with (
            patch("app.GameEngine", FakeEngine),
            patch("app.save_run"),
            patch("elixis.process_trace.llm_public_config", return_value=model_config),
        ):
            result = run_pipeline("Batman and Athena")

        self.assertEqual(result["output"], result["stage3_output"])
        self.assertEqual(result["stage3_output"], result["stage3_soulmd"])
        self.assertEqual(result["process_trace"]["lens"], "identity")
        self.assertEqual(result["process_trace"]["model"]["model"], "glm-5.1")
        self.assertEqual(
            result["process_trace"]["pattern_matching"]["method"],
            "0.7 LLM classification + 0.3 keyword/theme/type/knowledge scoring",
        )
        self.assertEqual(
            result["process_trace"]["pattern_matching"]["top_patterns"][0]["name"],
            "Wisdom & Knowledge",
        )
        self.assertEqual(result["process_trace"]["entities"][0]["name"], "Athena")
        self.assertEqual(result["threads"][0]["relationship"], "complements")
        self.assertEqual(result["process_trace"]["pattern_matching"]["thread_count"], 1)

    def test_game_pipeline_includes_normalized_output_alias(self):
        class FakeBead:
            def to_dict(self):
                return {
                    "canonical": "Athena",
                    "type": "mythological",
                    "themes": ["wisdom", "strategy"],
                    "traits": ["strategic clarity"],
                    "confidence": 0.92,
                }

        class FakeThread:
            def to_dict(self):
                return {
                    "bead_a": "Athena",
                    "bead_b": "Batman",
                    "relationship": "complements",
                    "strength": 0.8,
                    "isomorphic": True,
                    "domains_bridged": ["spirituality", "literature"],
                    "evidence": ["Shared themes: strategy"],
                }

        class FakeEngine:
            def __init__(self):
                self.state = MagicMock()
                self.state.beads = [FakeBead()]
                self.state.threads = [FakeThread()]
                self.state.tensions = []
                self.state.metadata = {
                    "pattern_graph": {
                        "patterns": [
                            {
                                "id": "wisdom",
                                "name": "Wisdom & Knowledge",
                                "probability": 0.88,
                                "supporting_entities": 1,
                                "sub_patterns": ["strategy"],
                            }
                        ],
                        "bridges": [
                            {
                                "entity": "Athena",
                                "pattern_a": "Wisdom & Knowledge",
                                "score_a": 0.88,
                                "pattern_b": "Power & Ambition",
                                "score_b": 0.62,
                            }
                        ],
                        "threads": [FakeThread().to_dict()],
                        "thread_count": 1,
                        "cross_domain_thread_count": 1,
                        "analysis_notes": ["Athena supports strategic clarity."],
                        "emergent_topic": "Wisdom & Knowledge",
                        "consensus_score": 0.75,
                    },
                    "pattern_telemetry": {
                        "llm_available": True,
                        "llm_classification": {
                            "source": "llm",
                            "provider": "anthropic",
                            "model": "glm-5.1",
                            "tokens_in": 100,
                            "tokens_out": 40,
                            "max_tokens": 2492,
                        },
                    },
                }
                self.state.timings = {"declaration_ms": 12, "connection_ms": 34, "resolution_ms": 56}

            def run_full(self, brain_dump, lens="identity"):
                return "# Brand Output"

        model_config = {
            "provider": "anthropic",
            "model": "glm-5.1",
            "base_host": "api.z.ai",
            "classify_model": "glm-5.1",
        }
        with (
            patch("app.GameEngine", FakeEngine),
            patch("app.save_run"),
            patch("elixis.process_trace.llm_public_config", return_value=model_config),
        ):
            result = run_game_pipeline("Batman and Athena", lens="brand")

        self.assertEqual(result["output"], "# Brand Output")
        self.assertEqual(result["stage3_output"], "# Brand Output")
        self.assertIsNone(result["stage3_soulmd"])
        trace = result["process_trace"]
        self.assertEqual(trace["lens"], "brand")
        self.assertEqual(trace["model"]["model"], "glm-5.1")
        self.assertEqual(trace["phases"][2]["name"], "connection")
        self.assertEqual(trace["phases"][2]["model"], "glm-5.1")
        self.assertEqual(trace["phases"][2]["tokens_in"], 100)
        self.assertEqual(trace["phases"][2]["max_tokens"], 2492)
        self.assertEqual(trace["pattern_matching"]["classification_max_tokens"], 2492)
        self.assertEqual(trace["pattern_matching"]["top_patterns"][0]["probability"], 0.88)
        self.assertEqual(trace["pattern_matching"]["bridges"][0]["entity"], "Athena")
        self.assertEqual(trace["pattern_matching"]["consensus_score"], 0.75)
        self.assertEqual(result["thread_count"], 1)
        self.assertEqual(result["cross_domain_thread_count"], 1)
        self.assertEqual(result["threads"][0]["relationship"], "complements")
        self.assertEqual(trace["phases"][2]["thread_count"], 1)

    @patch.object(Handler, '_begin_sse_response')
    @patch.object(Handler, '_log')
    def test_game_stream_emits_process_trace_event(self, mock_log, mock_begin_sse):
        class FakeBead:
            def to_dict(self):
                return {
                    "canonical": "Athena",
                    "type": "mythological",
                    "themes": ["wisdom", "strategy"],
                    "traits": ["strategic clarity"],
                }

        class FakeState:
            def __init__(self):
                self.beads = [FakeBead()]
                self.threads = []
                self.tensions = []
                self.timings = {"declaration_ms": 1, "elaboration_ms": 2, "connection_ms": 3}
                self.metadata = {
                    "pattern_graph": {
                        "patterns": [
                            {
                                "id": "wisdom",
                                "name": "Wisdom & Knowledge",
                                "probability": 0.88,
                                "supporting_entities": 1,
                            }
                        ],
                        "bridges": [],
                        "threads": [
                            {
                                "bead_a": "Athena",
                                "bead_b": "Batman",
                                "relationship": "complements",
                                "strength": 0.8,
                                "isomorphic": True,
                                "domains_bridged": ["spirituality", "literature"],
                                "evidence": ["Shared themes: strategy"],
                            }
                        ],
                        "thread_count": 1,
                        "cross_domain_thread_count": 1,
                    },
                    "pattern_telemetry": {
                        "llm_available": True,
                        "llm_classification": {
                            "source": "llm",
                            "provider": "anthropic",
                            "model": "glm-5.1",
                        },
                    },
                }

        class FakeEngine:
            def __init__(self):
                self.state = FakeState()

            def declare_themes(self, brain_dump):
                return self.state

            def elaborate(self):
                return self.state

            def connect_domains(self):
                return self.state

            def resolve_stream(self, lens="identity", stage_timings=None):
                yield {"type": "soulmd_token", "content": "# Output"}
                self.state.timings["resolution_ms"] = 9
                yield {"type": "soulmd_done", "data": {"length": 8}}

        model_config = {
            "provider": "anthropic",
            "model": "glm-5.1",
            "base_host": "api.z.ai",
            "classify_model": "glm-5.1",
        }
        handler = _make_handler("POST", "/api/game/stream", body={"text": "Batman and Athena", "lens": "brand"})

        with (
            patch("app.GameEngine", FakeEngine),
            patch("app.save_run") as mock_save_run,
            patch("elixis.process_trace.llm_public_config", return_value=model_config),
        ):
            handler._handle_game_stream(start=0)

        events = [
            json.loads(line.removeprefix("data: "))
            for line in handler.wfile.getvalue().decode().splitlines()
            if line.startswith("data: ")
        ]
        event_types = [event["type"] for event in events]
        self.assertIn("process_trace", event_types)
        graph_event = [event for event in events if event["type"] == "graph"][0]
        self.assertEqual(graph_event["data"]["thread_count"], 1)
        self.assertEqual(graph_event["data"]["threads"][0]["relationship"], "complements")
        trace_events = [event for event in events if event["type"] == "process_trace"]
        self.assertEqual(len(trace_events), 2)
        trace_event = trace_events[0]
        final_trace_event = trace_events[-1]
        self.assertEqual(trace_event["data"]["lens"], "brand")
        self.assertEqual(trace_event["data"]["model"]["model"], "glm-5.1")
        self.assertEqual(
            trace_event["data"]["pattern_matching"]["top_patterns"][0]["name"],
            "Wisdom & Knowledge",
        )
        self.assertLess(event_types.index("process_trace"), event_types.index("soulmd_done"))
        final_trace_index = max(i for i, event_type in enumerate(event_types) if event_type == "process_trace")
        self.assertGreater(final_trace_index, event_types.index("soulmd_done"))
        self.assertEqual(final_trace_event["data"]["phases"][3]["duration_ms"], 9)
        mock_save_run.assert_called_once()
        self.assertEqual(mock_save_run.call_args.args[0], "Batman and Athena")
        self.assertEqual(mock_save_run.call_args.args[3], "# Output")
        self.assertEqual(mock_save_run.call_args.kwargs["lens"], "brand")

    @patch.object(Handler, '_begin_sse_response')
    @patch.object(Handler, '_log')
    def test_extract_stream_saves_single_complete_observable_run(self, mock_log, mock_begin_sse):
        class FakeBead:
            def to_dict(self):
                return {
                    "canonical": "Athena",
                    "type": "mythological",
                    "themes": ["wisdom"],
                    "traits": ["strategic clarity"],
                }

        class FakeState:
            def __init__(self):
                self.beads = [FakeBead()]
                self.threads = []
                self.tensions = []
                self.timings = {"declaration_ms": 1, "elaboration_ms": 2, "connection_ms": 3}
                self.metadata = {
                    "pattern_graph": {
                        "patterns": [{"name": "Wisdom"}],
                        "bridges": [],
                        "threads": [
                            {
                                "bead_a": "Athena",
                                "bead_b": "Batman",
                                "relationship": "complements",
                                "strength": 0.8,
                                "isomorphic": True,
                                "domains_bridged": ["spirituality", "literature"],
                                "evidence": ["Shared themes: strategy"],
                            }
                        ],
                        "thread_count": 1,
                        "cross_domain_thread_count": 1,
                    }
                }

        class FakeEngine:
            def __init__(self):
                self.state = FakeState()

            def declare_themes(self, brain_dump):
                return self.state

            def elaborate(self):
                return self.state

            def connect_domains(self):
                return self.state

            def resolve_stream(self, lens="identity", stage_timings=None):
                yield {"type": "soulmd_token", "content": "# "}
                yield {"type": "soulmd_token", "content": "Output"}
                yield {"type": "telemetry", "data": {"model": "glm-5.1"}}
                if stage_timings is not None:
                    stage_timings["stage3_synthesis_ms"] = 17
                yield {"type": "soulmd_done", "data": {"length": 8}}

        handler = _make_handler("POST", "/api/extract/stream", body={"brain_dump": "Batman and Athena"})

        with (
            patch("app.GameEngine", FakeEngine),
            patch("app.save_run") as mock_save_run,
        ):
            handler._handle_stream("Batman and Athena", start=0)

        mock_save_run.assert_called_once()
        self.assertEqual(mock_save_run.call_args.args[0], "Batman and Athena")
        self.assertEqual(mock_save_run.call_args.args[3], "# Output")
        self.assertEqual(mock_save_run.call_args.kwargs["lens"], "identity")
        self.assertEqual(mock_save_run.call_args.kwargs["telemetry"]["model"], "glm-5.1")
        events = [
            json.loads(line.removeprefix("data: "))
            for line in handler.wfile.getvalue().decode().splitlines()
            if line.startswith("data: ")
        ]
        graph_event = [event for event in events if event["type"] == "graph"][0]
        self.assertEqual(graph_event["data"]["thread_count"], 1)
        final_trace_event = [event for event in events if event["type"] == "process_trace"][-1]
        self.assertEqual(final_trace_event["data"]["pattern_matching"]["thread_count"], 1)
        self.assertEqual(final_trace_event["data"]["phases"][3]["duration_ms"], 17)


if __name__ == "__main__":
    unittest.main()
