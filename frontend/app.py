"""Frontend server — serves the React build from dist/.

During development, use ``npm run dev`` instead (Vite dev server with
hot-reload and API proxy). This server is for production: ``npm run build``
creates ``dist/``, and this script serves it.
"""

import mimetypes
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

_HERE = Path(__file__).parent
_DIST = _HERE / "dist"
_PORT = int(os.getenv("FRONTEND_PORT", "7860"))

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_DIST), **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    if not _DIST.exists():
        print("dist/ not found. Run 'npm run build' first, or use 'npm run dev' for development.")
        raise SystemExit(1)
    server = HTTPServer(("0.0.0.0", _PORT), Handler)
    print(f"Frontend running at http://localhost:{_PORT}")
    server.serve_forever()
