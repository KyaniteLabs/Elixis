"""HTTP server handler tests for app.py.

Tests the Handler class directly using mocked I/O streams,
without starting a real HTTP server.
"""

import io
import json
import unittest
from unittest.mock import patch, MagicMock

from app import Handler, _shutdown_requested


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
    def test_diagnostics_endpoint(self, mock_diag, mock_log, mock_header, mock_end, mock_cors, mock_resp):
        mock_diag.return_value = {"status": "ok", "total_runs": 0}
        handler = _make_handler("GET", "/api/diagnostics")
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
    def test_backups_endpoint(self, mock_list, mock_log, mock_json):
        mock_list.return_value = [{"name": "backup_1", "size_bytes": 100}]
        handler = _make_handler("GET", "/api/backups")

        with patch.object(Handler, 'do_GET', Handler.do_GET):
            handler.do_GET()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("backups", data)


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
    def test_naming_no_name(self, mock_log, mock_json):
        handler = _make_handler("POST", "/api/naming", body={})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_json.assert_called_once()
        data = mock_json.call_args[0][0]
        self.assertIn("error", data)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    @patch.object(Handler, '_log')
    def test_post_404(self, mock_log, mock_end, mock_cors, mock_resp):
        handler = _make_handler("POST", "/api/nonexistent", body={})

        with patch.object(Handler, 'do_POST', Handler.do_POST):
            handler.do_POST()

        mock_resp.assert_called_with(404)


class TestCorsHeaders(unittest.TestCase):
    """Test CORS and security headers."""

    @patch.object(Handler, 'send_header')
    def test_cors_headers_present(self, mock_header):
        handler = _make_handler("GET", "/")
        handler._send_cors_headers()

        headers_sent = {call[0][0]: call[0][1] for call in mock_header.call_args_list}
        self.assertIn("Access-Control-Allow-Origin", headers_sent)
        self.assertIn("Access-Control-Allow-Methods", headers_sent)
        self.assertIn("X-Request-ID", headers_sent)

    @patch.object(Handler, 'send_response')
    @patch.object(Handler, 'send_header')
    @patch.object(Handler, '_send_cors_headers')
    @patch.object(Handler, 'end_headers')
    def test_options_returns_204(self, mock_end, mock_cors, mock_header, mock_resp):
        handler = _make_handler("OPTIONS", "/api/extract")

        with patch.object(Handler, 'do_OPTIONS', Handler.do_OPTIONS):
            handler.do_OPTIONS()

        mock_resp.assert_called_with(204)


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


if __name__ == "__main__":
    unittest.main()
