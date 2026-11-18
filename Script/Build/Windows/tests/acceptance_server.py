"""Temporary transfer/report endpoint bound to the private libvirt test network."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import re
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, default=40890)
    args = parser.parse_args()
    root = args.root.resolve()
    reports = root.parent / 'reports'
    reports.mkdir(exist_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        extensions_map = dict(SimpleHTTPRequestHandler.extensions_map, **{'.ps1': 'text/plain; charset=utf-8'})
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def do_PUT(self):
            path = urlsplit(self.path).path
            if not re.fullmatch(r'/reports/[A-Za-z0-9_.-]{1,100}', path):
                self.send_error(400)
                return
            size = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= size <= 20 * 1024 ** 2:
                self.send_error(413)
                return
            data = self.rfile.read(size)
            if len(data) != size:
                self.send_error(400)
                return
            (reports / path.rsplit('/', 1)[1]).write_bytes(data)
            self.send_response(200)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def log_message(self, fmt, *a):
            if '/command.ps1' in str(a) and '404' in str(a):
                return
            super().log_message(fmt, *a)

    server = ThreadingHTTPServer(('192.168.122.1', args.port), Handler)
    print(f'Test-only endpoint: http://192.168.122.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
