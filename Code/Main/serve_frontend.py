#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serve the built frontend dist without requiring Node.js on customer machines."""

from __future__ import annotations

import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class FrontendRequestHandler(SimpleHTTPRequestHandler):
    """Static file handler with SPA index fallback."""

    def translate_path(self, path: str) -> str:
        parsed_path = urlparse(path).path
        relative_path = unquote(parsed_path).lstrip("/")
        candidate = (Path(self.directory) / relative_path).resolve()
        dist_root = Path(self.directory).resolve()

        try:
            candidate.relative_to(dist_root)
        except ValueError:
            return str(dist_root / "index.html")

        if candidate.is_file():
            return str(candidate)
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return str(candidate / "index.html")
        return str(dist_root / "index.html")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MonGSV frontend dist server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, required=True, help="Bind port")
    parser.add_argument("--dist", required=True, help="Frontend dist directory")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    dist_dir = Path(args.dist).resolve()
    index_file = dist_dir / "index.html"
    if not index_file.is_file():
        print(f"[frontend] dist index not found: {index_file}", flush=True)
        return 1

    handler = lambda *handler_args, **handler_kwargs: FrontendRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(dist_dir),
        **handler_kwargs,
    )
    server = ReusableThreadingHTTPServer((args.host, args.port), handler)
    print(f"[frontend] serving {dist_dir} at http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
