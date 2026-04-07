"""Soulcraft — The Glass Bead Game for AI Personas.

Usage: python app.py [--port PORT]
"""

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from soulcraft.entities import extract_entities
from soulcraft.patterns import build_pattern_graph
from soulcraft.synthesis import synthesize_soulmd, synthesize_soulmd_stream
from soulcraft.traces import save_run, log_request, get_diagnostics, get_recent_runs

PORT = 3110
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "soulcraft", "templates")


def run_pipeline(brain_dump):
    """Run the full 3-stage pipeline on a brain dump string."""
    if not brain_dump or len(brain_dump.strip()) < 3:
        return {"error": "Brain dump is empty or too short"}

    timings = {}

    t0 = time.time()
    entities = extract_entities(brain_dump)
    timings["stage1_extract_ms"] = int((time.time() - t0) * 1000)

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
    def do_GET(self):
        start = time.time()
        if self.path in ("", "/"):
            self._serve_file("landing.html", "text/html")
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/diagnostics":
            self._json_response(get_diagnostics())
            self._log("GET", self.path, 200, start)
        elif self.path == "/api/runs":
            self._json_response({"runs": get_recent_runs(50)})
            self._log("GET", self.path, 200, start)
        else:
            self._serve_static(self.path)
            self._log("GET", self.path, 200, start)

    def do_POST(self):
        start = time.time()
        if self.path == "/api/extract":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            brain_dump = data.get("brain_dump", "")

            if not brain_dump or len(brain_dump.strip()) < 3:
                self._json_response({"error": "Brain dump is empty or too short"}, 400)
                return

            # Check if client wants streaming
            accept = self.headers.get("Accept", "")
            if "text/event-stream" in accept or data.get("stream"):
                self._handle_stream(brain_dump, start)
            else:
                result = run_pipeline(brain_dump)
                status = 200 if "error" not in result else 400
                self._json_response(result, status)
                self._log("POST", self.path, status, start, extra={
                    "entity_count": len(result.get("stage1_entities", [])),
                    "emergent": result.get("stage2_graph", {}).get("emergent_topic"),
                    "soulmd_length": len(result.get("stage3_soulmd", "")),
                    "timings": result.get("timings"),
                })
        else:
            self.send_response(404)
            self.end_headers()
            self._log("POST", self.path, 404, start)

    def _handle_stream(self, brain_dump, start):
        """Handle a streaming SSE response."""
        from soulcraft.entities import extract_entities
        from soulcraft.patterns import build_pattern_graph

        entities = extract_entities(brain_dump)
        graph = build_pattern_graph(entities, brain_dump)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        for event in synthesize_soulmd_stream(entities, graph):
            payload = json.dumps(event)
            self.wfile.write(f"data: {payload}\n\n".encode())
            self.wfile.flush()

        duration_ms = (time.time() - start) * 1000
        self._log("POST", "/api/extract", 200, start, extra={
            "streamed": True,
            "entity_count": len(entities),
            "emergent": graph.get("emergent_topic"),
        })

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _log(self, method, path, status, start, extra=None):
        duration_ms = (time.time() - start) * 1000
        log_request(method, path, status, duration_ms, extra)

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
