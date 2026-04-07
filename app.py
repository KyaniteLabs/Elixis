"""Soulcraft — The Glass Bead Game for AI Personas.

Usage: python app.py [--port PORT]
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from soulcraft.entities import extract_entities
from soulcraft.patterns import build_pattern_graph
from soulcraft.synthesis import synthesize_soulmd

PORT = 3110
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "soulcraft", "templates")


def run_pipeline(brain_dump):
    """Run the full 3-stage pipeline on a brain dump string."""
    if not brain_dump or len(brain_dump.strip()) < 3:
        return {"error": "Brain dump is empty or too short"}

    entities = extract_entities(brain_dump)
    graph = build_pattern_graph(entities, brain_dump)
    soulmd = synthesize_soulmd(entities, graph)

    return {
        "stage1_entities": entities,
        "stage2_graph": graph,
        "stage3_soulmd": soulmd,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("", "/"):
            self._serve_file("landing.html", "text/html")
        else:
            self._serve_static(self.path)

    def do_POST(self):
        if self.path == "/api/extract":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            result = run_pipeline(data.get("brain_dump", ""))

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(TEMPLATE_DIR, filename)
        if not os.path.isfile(filepath):
            self.send_response(404)
            self.end_headers()
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_static(self, path):
        """Serve static files from templates dir (css, js, images)."""
        # Strip leading slash
        filename = path.lstrip("/")
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

    def log_message(self, format, *args):
        pass  # suppress per-request logging


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    port = PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    server = ThreadedHTTPServer(("0.0.0.0", port), Handler)
    print(f"Soulcraft running on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
