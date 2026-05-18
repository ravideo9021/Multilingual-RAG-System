"""Frontend server — serves the standalone HTML/JS chat application.

Uses a minimal HTTP server (no Gradio components). The entire UI is
in index.html which talks directly to the FastAPI backend.
"""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

_HERE = Path(__file__).parent
_HTML = (_HERE / "index.html").read_bytes()
_PORT = int(os.getenv("FRONTEND_PORT", "7860"))


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(_HTML)

    def log_message(self, format, *args):
        # Suppress request logging noise
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", _PORT), Handler)
    print(f"Frontend running at http://localhost:{_PORT}")
    server.serve_forever()
