"""Real loopback HTTP boundary tests; synthesis output is an explicit fixture.

No live inference, production service, browser or external network is exercised.
"""
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import app


class HttpBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.server = app.ThreadedHTTPServer(('127.0.0.1', 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, payload=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            body = json.dumps(payload) if payload is not None else None
            conn.request(method, path, body, headers or {})
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_admin_rejects_missing_token_over_socket(self):
        with patch.object(app, 'ADMIN_API_KEY', 'fixture-only-not-a-secret'):
            status, body = self.request('GET', '/api/diagnostics')
        self.assertEqual(status, 401)
        self.assertIn('error', body)

    def test_invalid_lens_does_not_call_pipeline(self):
        with patch.object(app, 'run_game_pipeline') as pipeline:
            status, body = self.request('POST', '/api/game',
                                        {'brain_dump': 'test creative influences', 'lens': 'invalid'})
        self.assertEqual(status, 400)
        self.assertIn('error', body)
        pipeline.assert_not_called()

    def test_game_round_trip_with_fixture_backend(self):
        fixture = {'lens': 'brand', 'output': '# Fixture brand', 'timings': {}}
        with patch.object(app, 'run_game_pipeline', return_value=fixture) as pipeline:
            status, body = self.request('POST', '/api/game',
                                        {'brain_dump': 'test creative influences', 'lens': 'brand'})
        self.assertEqual(status, 200)
        self.assertEqual(body, fixture)
        pipeline.assert_called_once_with('test creative influences', lens='brand')
