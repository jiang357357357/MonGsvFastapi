"""Install pinned official V5 assets without replacing existing model files."""
import argparse
import hashlib
import os
import re
import shutil
import ssl
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def download(target, workers=8, variant="all", transport="requests", attempts=4):
    if workers < 1:
        raise ValueError("workers must be positive")
    if attempts < 1:
        raise ValueError("attempts must be positive")
    if transport == "curl" and not shutil.which("curl"):
        raise RuntimeError("curl is required for --transport curl")
    target = Path(target).resolve()
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
    sizes = CONFIG["v5_sizes"]
    for filename, expected in CONFIG["v5_files"].items():
        if variant != "all" and Path(filename).name != ("vocoder.pth" if variant == "vocoder" else f"s2G{variant}.pth"):
            continue
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
        for attempt in range(attempts):
            try:
                with session().get(url, params={"download": "true", "_refresh": str(int(time.time()))},
                                   headers={"Range": "bytes=0-0"}, stream=True, timeout=(15, 30)) as response:
                    response.raise_for_status()
                    download_url = response.url
                break
            except requests.RequestException:
                if attempt == attempts - 1:
                    raise
                time.sleep(min(attempt + 1, 6))

        def get_part(index):
            start, end = index * chunk_size, min(size, (index + 1) * chunk_size) - 1
            part = parts / f"{index:05d}"
            if part.exists() and part.stat().st_size == end - start + 1:
                return
            for attempt in range(attempts):
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
                    if transport == "curl":
                        body = temporary.with_suffix(".download")
                        headers = temporary.with_suffix(".headers")
                        try:
                            command = [
                                "curl", "--silent", "--show-error", "--location", "--http1.1",
                                "--connect-timeout", "20", "--max-time", "600",
                                "--range", f"{range_start}-{end}", "--dump-header", str(headers),
                                "--output", str(body), download_url,
                            ]
                            if attempt % 2 == 0:
                                command[1:1] = ["--tlsv1.2", "--tls-max", "1.2"]
                            result = subprocess.run(command, capture_output=True, timeout=620)
                            ranges = re.findall(r"(?im)^content-range:\s*([^\r\n]+)", headers.read_text())
                            if not ranges or ranges[-1] != f"bytes {range_start}-{end}/{size}":
                                raise RuntimeError(f"Invalid curl response: exit={result.returncode}, range={ranges[-1] if ranges else 'missing'}")
                            if not body.exists() or not 0 < body.stat().st_size <= end - range_start + 1:
                                raise RuntimeError("curl returned an invalid download part")
                            with temporary.open("ab" if offset else "wb") as stream, body.open("rb") as source:
                                shutil.copyfileobj(source, stream)
                            if result.returncode or temporary.stat().st_size != end - start + 1:
                                raise RuntimeError("Incomplete curl download; saved bytes for resume")
                            temporary.replace(part)
                        finally:
                            body.unlink(missing_ok=True)
                            headers.unlink(missing_ok=True)
                        return
                    with session().get(download_url,
                                      headers={"Range": f"bytes={range_start}-{end}"}, stream=True,
                                      timeout=(15, 30)) as result:
                        result.raise_for_status()
                        if result.status_code != 206 or result.headers.get("Content-Range", "").split("/")[0] != f"bytes {range_start}-{end}":
                            raise RuntimeError("Server did not honor the requested byte range")
                        with temporary.open("ab" if offset else "wb") as stream:
                            for chunk in result.iter_content(64 * 1024):
                                stream.write(chunk)
                        if temporary.stat().st_size != end - start + 1:
                            raise RuntimeError("Incomplete download part")
                        temporary.replace(part)
                    return
                except (requests.RequestException, RuntimeError):
                    if attempt == attempts - 1:
                        raise
                    time.sleep(min(attempt + 1, 6))

        print(f"Downloading {filename}: {size} bytes, {count} resumable parts", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(get_part, index) for index in range(count)]
            for completed, future in enumerate(as_completed(futures), 1):
                future.result()
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
    parser.add_argument("--variant", choices=["all", "v5dev", "v5turbo", "vocoder"], default="all")
    parser.add_argument("--transport", choices=["requests", "curl"], default="requests")
    parser.add_argument("--attempts", type=int, default=4)
    args = parser.parse_args()
    download(args.target, args.workers, args.variant, args.transport, args.attempts)
