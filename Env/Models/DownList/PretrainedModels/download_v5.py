"""Install pinned official V5 assets without replacing existing model files."""
import argparse
import hashlib
import os
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from module_config import CONFIG

_local = threading.local()


class CompatibleTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def session():
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
        _local.session.mount("https://", CompatibleTLSAdapter(max_retries=Retry(total=3, backoff_factor=1,
                                      status_forcelist=[429, 500, 502, 503, 504])))
    return _local.session


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(target, workers=8):
    target = Path(target).resolve()
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
    sizes = CONFIG["v5_sizes"]
    for filename, expected in CONFIG["v5_files"].items():
        path = target / filename
        if path.exists() and sha256(path) == expected:
            print("Verified cached model:", path, flush=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        parts = path.with_name(path.name + ".parts")
        parts.mkdir(exist_ok=True)
        size, chunk_size = sizes[filename], 4 * 1024 * 1024
        count = (size + chunk_size - 1) // chunk_size
        url = f"{endpoint}/{CONFIG['v5_repo']}/resolve/{CONFIG['v5_revision']}/{filename}"
        # Resolve once so every part can use the CDN without repeating Hub
        # metadata requests. The signed public asset URL is kept in memory.
        with session().get(url, params={"download": "true"}, headers={"Range": "bytes=0-0"},
                           stream=True, timeout=(15, 30)) as response:
            response.raise_for_status()
            download_url = response.url

        def get_part(index):
            start, end = index * chunk_size, min(size, (index + 1) * chunk_size) - 1
            part = parts / f"{index:05d}"
            if part.exists() and part.stat().st_size == end - start + 1:
                return
            for attempt in range(4):
                try:
                    temporary = part.with_suffix(".partial")
                    offset = temporary.stat().st_size if temporary.exists() else 0
                    if offset > end - start + 1:
                        temporary.unlink()
                        offset = 0
                    range_start = start + offset
                    if range_start > end:
                        temporary.replace(part)
                        return
                    with session().get(download_url,
                                      headers={"Range": f"bytes={range_start}-{end}"}, stream=True,
                                      timeout=(15, 30)) as result:
                        result.raise_for_status()
                        if result.status_code != 206 or result.headers.get("Content-Range", "").split("/")[0] != f"bytes {range_start}-{end}":
                            raise RuntimeError("Server did not honor the requested byte range")
                        with temporary.open("ab" if offset else "wb") as stream:
                            for chunk in result.iter_content(1024 * 1024):
                                stream.write(chunk)
                        if temporary.stat().st_size != end - start + 1:
                            raise RuntimeError("Incomplete download part")
                        temporary.replace(part)
                    return
                except (requests.RequestException, RuntimeError):
                    if attempt == 3:
                        raise
                    time.sleep(attempt + 1)

        print(f"Downloading {filename}: {size} bytes, {count} resumable parts", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for completed, _ in enumerate(executor.map(get_part, range(count)), 1):
                if completed % 16 == 0 or completed == count:
                    print(f"{filename}: {completed}/{count}", flush=True)
        temporary = path.with_suffix(".partial")
        with temporary.open("wb") as stream:
            for index in range(count):
                with (parts / f"{index:05d}").open("rb") as part:
                    for chunk in iter(lambda: part.read(8 * 1024 * 1024), b""):
                        stream.write(chunk)
        if sha256(temporary) != expected:
            raise RuntimeError("Model checksum mismatch: " + str(temporary))
        temporary.replace(path)
        for part in parts.iterdir():
            part.unlink()
        parts.rmdir()
        print("Verified model:", path, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=str(Path(__file__).resolve().parents[4] / CONFIG["default_path"]))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    download(args.target, args.workers)
