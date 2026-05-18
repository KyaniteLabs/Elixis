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
                return {"canonical": "Athena"}

        class FakeEngine:
            def __init__(self):
                self.state = MagicMock()
                self.state.beads = [FakeBead()]
                self.state.metadata = {"pattern_graph": {}}
                self.state.timings = {}

            def run_full(self, brain_dump, lens="identity"):
                return "# SOUL.md"

        with patch("app.GameEngine", FakeEngine), patch("app.save_run"):
            result = run_pipeline("Batman and Athena")

        self.assertEqual(result["output"], result["stage3_output"])
        self.assertEqual(result["stage3_output"], result["stage3_soulmd"])

    def test_game_pipeline_includes_normalized_output_alias(self):
        class FakeBead:
            def to_dict(self):
                return {"canonical": "Athena"}

        class FakeThread:
            def to_dict(self):
                return {"bead_a": "Athena", "bead_b": "Wisdom"}

        class FakeEngine:
            def __init__(self):
                self.state = MagicMock()
                self.state.beads = [FakeBead()]
                self.state.threads = [FakeThread()]
                self.state.tensions = []
                self.state.metadata = {"pattern_graph": {}}
                self.state.timings = {}

            def run_full(self, brain_dump, lens="identity"):
                return "# Brand Output"

        with patch("app.GameEngine", FakeEngine):
            result = run_game_pipeline("Batman and Athena", lens="brand")

        self.assertEqual(result["output"], "# Brand Output")
        self.assertEqual(result["stage3_output"], "# Brand Output")
        self.assertIsNone(result["stage3_soulmd"])


if __name__ == "__main__":
    unittest.main()
