"""Serve the generated OM locally without console logging."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *args):
        return


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=root, **kwargs)
    ThreadingHTTPServer(("127.0.0.1", 8766), handler).serve_forever()
