"""Resolve the repository lock for Windows CPython 3.10 and assemble its wheels.

The build host may be Linux. No Windows extension is imported on the build host.
All binary wheels must have a compatible Windows/abi3 tag, and downloads are
checked against the upstream lock/index SHA-256 before extraction.
"""
from __future__ import annotations
import concurrent.futures
import csv
import hashlib
import html
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.parse
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

ENVIRONMENT = dict(default_environment(), os_name='nt', sys_platform='win32',
                   platform_system='Windows', platform_machine='AMD64',
                   platform_release='10', platform_version='10.0.19045',
                   python_version='3.10', python_full_version='3.10.20',
                   implementation_name='cpython', platform_python_implementation='CPython',
                   implementation_version='3.10.20', extra='')
TAGS = list(cpython_tags((3, 10), ['cp310'], ['win_amd64'])) + list(compatible_tags((3, 10), 'cp310', ['win_amd64']))
TAG_RANK = {tag: index for index, tag in enumerate(TAGS)}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def fetch(url: str, path: Path, sha256: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and (not sha256 or digest(path) == sha256):
        return path
    partial = path.with_name(path.name + '.part')
    for attempt in range(4):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {'User-Agent': 'MonGSV-Windows-Builder/1.0'}
            if offset:
                headers['Range'] = f'bytes={offset}-'
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
                resumed = offset > 0 and response.status == 206
                with partial.open('ab' if resumed else 'wb') as output:
                    shutil.copyfileobj(response, output, 1024 * 1024)
            if sha256 and digest(partial) != sha256:
                partial.unlink()
                raise ValueError(f'SHA-256 mismatch: {path.name}')
            partial.replace(path)
            return path
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')


def target_requirements(export: Path) -> list[Requirement]:
    result = []
    for line in export.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate(ENVIRONMENT):
            result.append(requirement)
    return result


def wheel_score(filename: str) -> int | None:
    try:
        _, _, _, tags = parse_wheel_filename(filename)
    except ValueError:
        return None
    scores = [TAG_RANK[tag] for tag in tags if tag in TAG_RANK]
    return min(scores) if scores else None


def select_wheel(wheels: list[dict]) -> dict | None:
    options = []
    for entry in wheels:
        filename = urllib.parse.unquote(urllib.parse.urlparse(entry['url']).path.split('/')[-1])
        score = wheel_score(filename)
        if score is not None:
            options.append((score, filename, entry))
    if not options:
        return None
    _, filename, entry = min(options, key=lambda item: item[:2])
    return dict(entry, filename=filename)


def torch_wheel(name: str, version: str) -> dict:
    import re
    index = f'https://download.pytorch.org/whl/cu128/{name}/'
    with urllib.request.urlopen(index, timeout=45) as response:
        content = response.read().decode()
    options = []
    for link in re.findall(r'href="([^"]+)"', content):
        url = urllib.parse.urljoin(index, html.unescape(link))
        filename = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit('/', 1)[-1])
        if wheel_score(filename) is None:
            continue
        wheel_name, wheel_version, _, _ = parse_wheel_filename(filename)
        if canonicalize_name(wheel_name) != name or wheel_version != Version(version):
            continue
        checksum = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment).get('sha256', [None])[0]
        if not checksum:
            raise ValueError(f'No published SHA-256 for {filename}')
        options.append({'url': url.split('#')[0], 'hash': 'sha256:' + checksum})
    selected = select_wheel(options)
    if selected is None:
        raise RuntimeError(f'No Windows CUDA 12.8 wheel for {name}=={version}')
    return selected


def prepare(root: Path, destination: Path, workers: int = 6) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    export = destination / 'requirements-all.txt'
    subprocess.run(['uv', 'export', '--frozen', '--no-hashes', '--no-emit-project',
                    '--format', 'requirements-txt', '--output-file', str(export)],
                   cwd=root, check=True, stdout=subprocess.DEVNULL)
    requirements = target_requirements(export)
    lock = tomllib.loads((root / 'uv.lock').read_text())
    packages = {(canonicalize_name(p['name']), p['version']): p for p in lock['package']}
    plan = []
    for requirement in requirements:
        name = canonicalize_name(requirement.name)
        version = next(spec.version for spec in requirement.specifier if spec.operator == '==')
        package = packages[name, version]
        wheel = torch_wheel(name, version) if name in {'torch', 'torchaudio', 'torchvision'} else select_wheel(package.get('wheels', []))
        if wheel is None:
            source = package.get('sdist')
            if not source:
                raise RuntimeError(f'No Windows wheel or source: {name}=={version}')
            cache = root / 'Temp/WinBuild/sdists'
            filename = urllib.parse.urlparse(source['url']).path.split('/')[-1]
            archive = fetch(source['url'], cache / filename, source['hash'].split(':', 1)[1])
            subprocess.run([shutil.which('pip') or sys.executable, 'wheel', '--no-deps',
                            '--wheel-dir', str(destination), str(archive)], check=True)
            built = [f for f in destination.glob('*.whl')
                     if canonicalize_name(parse_wheel_filename(f.name)[0]) == name
                     and parse_wheel_filename(f.name)[1] == Version(version)
                     and wheel_score(f.name) is not None]
            if not built:
                raise RuntimeError(f'{name} requires a Windows-native build; a Linux extension cannot be shipped.')
            file = built[0]
            wheel = {'filename': file.name, 'url': source['url'], 'hash': 'sha256:' + digest(file), 'built_pure': True}
        plan.append(dict(wheel, name=name, version=version))
    (destination / 'index.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')

    def download(item):
        file = destination / item['filename']
        fetch(item['url'], file, item['hash'].split(':', 1)[1])
        print(f"[wheel] {file.name} ({file.stat().st_size / 1024 / 1024:.1f} MiB)", flush=True)
        return item

    print(f'[wheel] Preparing {len(plan)} Windows/pure Python distributions.', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(download, plan))
    lines = ['# Windows x64 / CPython 3.10 / CUDA 12.8; complete locked dependency set.']
    lines += [f"{p['name']}=={p['version']} --hash={p['hash']}" for p in plan]
    (destination / 'requirements-win.txt').write_text('\n'.join(lines) + '\n')
    return plan


def install_wheels(packages: Path, runtime: Path, plan: list[dict]) -> dict:
    site = runtime / 'Lib' / 'site-packages'
    site.mkdir(parents=True, exist_ok=True)
    # Standalone CPython already includes bootstrap setuptools. Remove mismatched
    # versions through their RECORD before overlaying the repository's lock.
    # Keeping both dist-info directories makes metadata.version() nondeterministic.
    expected = {p['name']: p['version'] for p in plan}
    for info in site.glob('*.dist-info'):
        metadata_file = info / 'METADATA'
        if not metadata_file.is_file():
            continue
        metadata = BytesParser().parsebytes(metadata_file.read_bytes())
        name = canonicalize_name(metadata['Name'])
        if name in expected and metadata['Version'] != expected[name]:
            record = info / 'RECORD'
            if not record.is_file():
                raise ValueError(f'Cannot replace distribution without RECORD: {info.name}')
            for row in csv.reader(record.read_text(encoding='utf-8').splitlines()):
                target = (site / row[0]).resolve()
                if not target.is_relative_to(runtime.resolve()):
                    raise ValueError(f'Bootstrap RECORD escapes runtime: {row[0]}')
                if target.is_file():
                    target.unlink()
            shutil.rmtree(info, ignore_errors=True)
    installed = []
    # ONNX Runtime GPU owns the import package when both metadata distributions
    # are required by the upstream lock (Chroma asks for the CPU distribution).
    ordered = sorted(plan, key=lambda p: (p['name'] == 'onnxruntime-gpu', p['name']))
    for package in ordered:
        file = packages / package['filename']
        if wheel_score(file.name) is None or digest(file) != package['hash'].split(':', 1)[1]:
            raise ValueError(f'Invalid wheel: {file.name}')
        with zipfile.ZipFile(file) as wheel:
            for member in wheel.infolist():
                if member.is_dir():
                    continue
                name = member.filename
                parts = Path(name).parts
                if parts[0].endswith('.data'):
                    category = parts[1]
                    base = site if category in {'purelib', 'platlib'} else runtime / 'Scripts' if category == 'scripts' else runtime
                    name = '/'.join(parts[2:])
                else:
                    base = site
                target = (base / name).resolve()
                if not target.is_relative_to(base.resolve()):
                    raise ValueError(f'Wheel path escapes destination: {name}')
                target.parent.mkdir(parents=True, exist_ok=True)
                with wheel.open(member) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
            installed.append(package['name'])
    return {'count': len(installed), 'names': installed, 'site_packages': str(site)}


def validate_dependency_metadata(packages: Path, plan: list[dict]) -> list[str]:
    versions = {p['name']: Version(p['version']) for p in plan}
    errors = []
    for package in plan:
        with zipfile.ZipFile(packages / package['filename']) as wheel:
            metadata_name = next(n for n in wheel.namelist() if n.endswith('.dist-info/METADATA'))
            metadata = BytesParser().parsebytes(wheel.read(metadata_name))
        for line in metadata.get_all('Requires-Dist', []):
            requirement = Requirement(line)
            if requirement.marker and not requirement.marker.evaluate(ENVIRONMENT):
                continue
            name = canonicalize_name(requirement.name)
            if name not in versions:
                errors.append(f"{package['name']}: missing {requirement}")
            elif requirement.specifier and versions[name] not in requirement.specifier:
                errors.append(f"{package['name']}: {name}=={versions[name]} does not satisfy {requirement}")
    return errors


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    destination = root / 'Temp/WinBuild/packages'
    plan = prepare(root, destination)
    errors = validate_dependency_metadata(destination, plan)
    (destination / 'dependency-errors.json').write_text(json.dumps(errors, indent=2) + '\n')
    if errors:
        raise SystemExit('\n'.join(errors))
