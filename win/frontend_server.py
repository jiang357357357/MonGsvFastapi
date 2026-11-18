"""Offline SPA server with runtime backend configuration, bound to loopback."""
from __future__ import annotations
import argparse
import functools
import json
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'app'))
from Code.Main.serve_frontend import FrontendRequestHandler


class Handler(FrontendRequestHandler):
    backend_port = 40302

    def do_GET(self):
        if self.path.split('?', 1)[0] == '/mon-config.js':
            payload = ('window.__MON_GSV_RUNTIME__ = ' + json.dumps({'backendHost': '127.0.0.1', 'backendPort': self.backend_port}) + ';\n').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=40031)
    parser.add_argument('--backend-port', type=int, default=40302)
    args = parser.parse_args(argv)
    dist = ROOT / 'app' / 'Code' / 'GptSov_Front' / 'dist'
    if not (dist / 'index.html').is_file():
        raise SystemExit('Missing frontend dist')
    Handler.backend_port = args.backend_port
    server = ThreadingHTTPServer(('127.0.0.1', args.port), functools.partial(Handler, directory=str(dist)))
    print(f'Frontend: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
