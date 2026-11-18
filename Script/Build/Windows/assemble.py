"""Build a relocatable Windows directory without importing its native modules.

Run on the repository build host with Python >=3.11 and packaging installed:
  python3 Script/Build/Windows/assemble.py --stage all
The wheels and external archives have published SHA-256 checksums. Optional
--stage values allow interrupted large downloads/copies to be resumed.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import fnmatch
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tarfile
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from dependencies import digest, fetch, install_wheels, prepare, validate_dependency_metadata

REPO = Path(__file__).resolve().parents[3]
BUILD = Path(__file__).resolve().parent
WIN = REPO / 'win'
APP = WIN / 'app'
CACHE = REPO / 'Temp/WinBuild'
PACKAGES = CACHE / 'packages'
PYTHON = {
    'name': 'cpython-3.10.20+20260408-x86_64-pc-windows-msvc-install_only_stripped.tar.gz',
    'url': 'https://github.com/astral-sh/python-build-standalone/releases/download/20260408/cpython-3.10.20%2B20260408-x86_64-pc-windows-msvc-install_only_stripped.tar.gz',
    'sha256': '0c82f1db79251336ec5f80dfb4b39c3658c5043edf736a48c8cd168542d1a222',
}
FFMPEG = {
    'name': 'ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip',
    'url': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip',
    'sha256': '1645b960b41569d8e40266ee1f95b46922b180064f813608c08138a590020cb8',
}
MSVC = {
    'name': 'vc-redist-14.44.35211-x64.exe',
    'url': 'https://download.visualstudio.microsoft.com/download/pr/990c720a-46ce-4dc7-87b9-c2eb615d34b9/CC0FF0EB1DC3F5188AE6300FAEF32BF5BEEBA4BDD6E8E445A9184072096B713B/VC_redist.x64.exe',
    'sha256': 'cc0ff0eb1dc3f5188ae6300faef32bf5beeba4bdd6e8e445a9184072096b713b',
}
IGNORE = shutil.ignore_patterns('.git', '.gitignore', '.github', '__pycache__', '*.pyc', '*.pyo',
                               '*.so', '*.log', '*.part', 'node_modules', '.env', '.env.*', '.cache',
                               '.pytest_cache', '.DS_Store')


def copy_tree(source: Path, target: Path, extra=()):
    if not source.exists():
        raise FileNotFoundError(source)
    def ignore(directory, names):
        result = set(IGNORE(directory, names))
        result.update(n for n in names if any(fnmatch.fnmatch(n, pattern) for pattern in extra))
        return result
    def copy_file(src, dst):
        original, output = Path(src), Path(dst)
        if output.is_file() and original.stat().st_size == output.stat().st_size and original.stat().st_mtime_ns == output.stat().st_mtime_ns:
            return dst
        return shutil.copy2(src, dst)
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore, copy_function=copy_file)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def install_msvc_supplement(target: Path):
    """ONNX Runtime needs the MSVC std::filesystem DLL absent from Python/sklearn."""
    archive = CACHE / MSVC['name']
    fetch(MSVC['url'], archive, MSVC['sha256'])
    data = archive.read_bytes()
    folder = CACHE / 'msvc-supplement'
    folder.mkdir(parents=True, exist_ok=True)
    containers = []
    offset = 0
    while (offset := data.find(b'MSCF', offset)) >= 0:
        size = struct.unpack_from('<I', data, offset + 8)[0]
        if data[offset + 4:offset + 8] == b'\0' * 4 and 36 <= size <= len(data) - offset:
            cab = folder / f'container-{len(containers)}.cab'
            cab.write_bytes(data[offset:offset + size])
            output = folder / cab.stem
            subprocess.run(['7z', 'x', '-y', f'-o{output}', str(cab)], check=True, stdout=subprocess.DEVNULL)
            containers.append(output)
        offset += 4
    header = next(p for p in containers if (p / '0').is_file())
    manifest = ET.parse(header / '0').getroot()
    payload = next(e.attrib['SourcePath'] for e in manifest.iter()
                   if e.tag.endswith('Payload') and e.attrib.get('FilePath', '').lower().endswith('vcruntimeminimum_amd64\\cab1.cab'))
    cabinet = next(p / payload for p in containers if (p / payload).is_file())
    output = folder / 'x64-minimum'
    subprocess.run(['7z', 'x', '-y', f'-o{output}', str(cabinet)], check=True, stdout=subprocess.DEVNULL)
    shutil.copy2(output / 'msvcp140_1.dll_amd64', target / 'msvcp140_1.dll')
    license_payload = next(e.attrib['SourcePath'] for e in manifest.iter()
                           if e.tag.endswith('Payload') and e.attrib.get('FilePath') == 'license.rtf')
    license_dir = target / 'licenses/msvc-14.44.35211'
    license_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(header / license_payload, license_dir / 'license.rtf')
    write_json(license_dir / 'source.json', MSVC)


def relocate_role_metadata(metadata: dict, app: Path) -> dict:
    result = dict(metadata)
    for key in ['gpt_model_path', 'sov_model_path', 'prompt_audio_path']:
        value = result.get(key)
        if not value:
            continue
        normalized = str(value).replace('\\', '/')
        marker = normalized.find('Resources/Model/')
        relative = normalized[marker:] if marker >= 0 else normalized
        candidate = app / relative
        result[key] = relative if candidate.is_file() and candidate.resolve().is_relative_to(app.resolve()) else None
    for key in ['gpt_model_id', 'sov_model_id']:
        result[key] = None  # Catalog IDs are rebuilt from this installation.
    return result


def clear_role_assets(app: Path = APP):
    """The Windows distribution starts without server-specific trained roles."""
    model_root = app / 'Resources/Model'
    if model_root.is_symlink():
        raise ValueError('Refusing to clear a symlinked role directory')
    if model_root.exists():
        shutil.rmtree(model_root)
    model_root.mkdir(parents=True, exist_ok=True)
    for filename in ['roles.json', 'worlds.json']:
        (app / 'Data/Meta/FastApi' / filename).unlink(missing_ok=True)
    write_json(app.parent / 'packaging-notes.json', {
        'trained_role_models_included': False,
        'reference_audio_included': False,
        'source_workspaces_without_complete_weights': [],
        'uvr5_weights_in_source': (REPO / 'tools/uvr5/uvr5_weights').is_dir(),
    })


def payload():
    print('[payload] Copying application, base models and ASR; excluding trained roles.', flush=True)
    APP.mkdir(parents=True, exist_ok=True)
    for directory in ['Code', 'GPT_SoVITS', 'tools']:
        copy_tree(REPO / directory, APP / directory, extra=('GptSov_Front', 'Script', 'tests', 'G2PWModel_1.1.zip',
                  'speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'))
    for filename in ['config.py', 'LICENSE']:
        shutil.copy2(REPO / filename, APP / filename)
    for directory in ['Data/Logs/Text', 'Data/Temp', 'Data/Output', 'Data/Meta/FastApi', 'Resources/Train/Projects']:
        (APP / directory).mkdir(parents=True, exist_ok=True)
    clear_role_assets()
    # Start with base weights; users can train or import roles on Windows.
    tts = APP / 'GPT_SoVITS/configs/tts_infer.yaml'
    content = tts.read_text(encoding='utf-8')
    start = content.index('v1:\n')
    content = ('custom:\n  version: v2ProPlus\n  device: cpu\n  is_half: false\n'
               '  bert_base_path: GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large\n'
               '  cnhuhbert_base_path: GPT_SoVITS/pretrained_models/chinese-hubert-base\n'
               '  t2s_weights_path: GPT_SoVITS/pretrained_models/s1v3.ckpt\n'
               '  vits_weights_path: GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth\n' + content[start:])
    tts.write_text(content, encoding='utf-8')
    portable = APP / 'tools/portable_runtime.py'
    content = portable.read_text(encoding='utf-8').replace('RUNTIME_DIR = PROJECT_ROOT / "runtime"',
        'RUNTIME_DIR = PROJECT_ROOT.parent / "runtime" if (PROJECT_ROOT.parent / "runtime").is_dir() else PROJECT_ROOT / "runtime"')
    portable.write_text(content, encoding='utf-8')
    # Portable settings must not inherit another project's parent .monconfig.
    config_loader = APP / 'Code/FastApi/Base/monconfig.py'
    content = config_loader.read_text(encoding='utf-8')
    content = content.replace('                config_files.append(config_file)\n',
                              '                config_files.append(config_file)\n                break\n')
    config_loader.write_text(content, encoding='utf-8')
    # A fresh local configuration, rather than server addresses or Django secrets.
    (APP / '.monconfig').write_text('''[service]
NAME=MonGSV-Windows
VERSION=1.0.0
DESCRIPTION=GPT-SoVITS Windows local edition
[server]
HOST=127.0.0.1
PORT=40302
RELOAD=false
ENABLE_AUTH=false
[frontend]
HOST=127.0.0.1
PORT=40031
[monhub]
ENABLED=false
DISCOVERY_ENABLED=false
[paths]
MODELS_DIR=Resources/Model
OUTPUT_DIR=Data/Output
TEMP_DIR=Data/Temp
RESOURCE_META_DIR=Data/Meta/FastApi
[model]
PRETRAINED_MODELS_DIR=GPT_SoVITS/pretrained_models
UVR5_WEIGHTS_DIR=tools/uvr5/uvr5_weights
[gpu]
ENABLED=true
DEVICE=cuda
HALF_PRECISION=true
[log]
LEVEL=info
FILE=Data/Logs/Text/GSV.log
PLAIN_FILE=Data/Logs/Text/GSV_plain.log
[process]
WORKERS=1
''', encoding='utf-8')
    print('[payload] Complete.', flush=True)


def frontend(build=True):
    source = REPO / 'Code/GptSov_Front'
    if build:
        subprocess.run(['npm', 'run', 'build'], cwd=source, check=True)
    css = CACHE / 'tailwind.css'
    subprocess.run(['npm', 'exec', '--yes', '--registry=https://registry.npmjs.org/', '--package=tailwindcss@3.4.17', '--', 'tailwindcss',
                    '-c', str(BUILD / 'tailwind.config.cjs'), '-i', str(BUILD / 'tailwind-input.css'),
                    '-o', str(css), '--minify'], cwd=REPO, check=True)
    dist = APP / 'Code/GptSov_Front/dist'
    if dist.exists():
        shutil.rmtree(dist)
    copy_tree(source / 'dist', dist)
    shutil.copy2(css, dist / 'assets/tailwind.css')
    index = dist / 'index.html'
    html = index.read_text(encoding='utf-8')
    html = re.sub(r'\s*<script src="https://cdn\.tailwindcss\.com"></script>', '', html)
    html = re.sub(r'\s*@import url\([^;]+;', '', html)
    html = re.sub(r'<script type="importmap">.*?</script>', '', html, flags=re.S)
    html = html.replace("font-family: 'Noto Sans SC', 'Space Mono', monospace;",
                        'font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;')
    html = html.replace('<title>AmberFlux Interface</title>', '<title>MonGSV · 语音工作台</title>')
    html = html.replace('<head>', '<head>\n    <link rel="stylesheet" href="/assets/tailwind.css">\n    <script src="/mon-config.js"></script>', 1)
    index.write_text(html, encoding='utf-8')
    print('[frontend] Local JavaScript/CSS only; runtime API configuration enabled.', flush=True)


def safe_target(base: Path, name: str) -> Path:
    target = (base / name).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError(f'Archive path escapes destination: {name}')
    return target


def runtime():
    print('[runtime] Checking Python and FFmpeg archives.', flush=True)
    with concurrent.futures.ThreadPoolExecutor(2) as executor:
        list(executor.map(lambda item: fetch(item['url'], CACHE / item['name'], item['sha256']), [PYTHON, FFMPEG]))
    target = WIN / 'runtime'
    target.mkdir(exist_ok=True)
    with tarfile.open(CACHE / PYTHON['name']) as archive:
        for member in archive:
            parts = Path(member.name).parts
            if not parts or parts[0] != 'python':
                continue
            path = safe_target(target, '/'.join(parts[1:]))
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, path.open('wb') as output:
                    shutil.copyfileobj(source, output)
            else:
                raise ValueError(f'Unsupported Python archive entry: {member.name}')
    with zipfile.ZipFile(CACHE / FFMPEG['name']) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            parts = Path(member.filename).parts
            relative = Path(*parts[1:])
            if relative.parts[0] == 'bin':
                base, name = WIN / 'Tool/bin', str(Path(*relative.parts[1:]))
            elif relative.name.lower().startswith(('license', 'readme', 'build-info')) or relative.parts[0] == 'licenses':
                base, name = WIN / 'Tool/ffmpeg-info', str(relative)
            else:
                continue
            path = safe_target(base, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, path.open('wb') as output:
                shutil.copyfileobj(source, output)
    plan = json.loads((PACKAGES / 'index.json').read_text())
    errors = validate_dependency_metadata(PACKAGES, plan)
    if errors:
        raise RuntimeError('\n'.join(errors))
    print('[runtime] Installing verified Windows wheels.', flush=True)
    install_wheels(PACKAGES, target, plan)
    site = target / 'Lib/site-packages'
    # scikit-learn ships the same MSVC 14.44.35211 runtime as this CPython.
    # Make its unrenamed C++ runtime visible to Torch before sklearn is imported.
    for name in ['msvcp140.dll', 'vcomp140.dll']:
        shutil.copy2(site / 'sklearn/.libs' / name, target / name)
    install_msvc_supplement(target)
    shutil.copy2(site / 'scikit_learn-1.7.2.dist-info/licenses/COPYING', target / 'LICENSE-MSVC-and-scikit-learn.txt')
    shutil.copy2(BUILD / 'sitecustomize.py', site / 'sitecustomize.py')
    nltk_source = Path(os.environ.get('NLTK_DATA_SOURCE', str(Path.home() / 'nltk_data')))
    for resource in ['corpora/cmudict', 'taggers/averaged_perceptron_tagger', 'taggers/averaged_perceptron_tagger_eng']:
        copy_tree(nltk_source / resource, target / 'nltk_data' / resource)
    write_json(WIN / 'Tool/sources.json', [PYTHON, FFMPEG, MSVC])
    print('[runtime] Python, dependencies, dictionaries and FFmpeg installed.', flush=True)


def trim():
    """Keep runtime functionality/models; omit development and installation files."""
    for directory in ['Tool/ffmpeg-info/doc', 'app/Env', 'app/Code/Script']:
        path = WIN / directory
        if path.exists():
            shutil.rmtree(path)
    for filename in ['Tool/bin/ffplay.exe', 'app/README.md', 'app/pyproject.toml', 'app/uv.lock']:
        (WIN / filename).unlink(missing_ok=True)
    for directory in ['app', 'runtime']:
        for path in sorted((WIN / directory).rglob('__pycache__'), reverse=True):
            # Regenerable bytecode only; leave any source-less module intact.
            for file in path.glob('*.pyc'):
                if (path.parent / (file.name.split('.')[0] + '.py')).is_file():
                    file.unlink()
            if not any(path.iterdir()):
                path.rmdir()


def payload_entries():
    paths = [p for name in ['app', 'runtime', 'Tool'] for p in (WIN / name).rglob('*') if p.is_file()]
    paths += [WIN / name for name in ['MonGSV.exe', 'launcher.py', 'frontend_server.py', 'diagnose.py',
                                     'config.json', 'Start.cmd', 'Stop.cmd', 'Check.cmd', 'packaging-notes.json']]
    return [{'path': p.relative_to(WIN).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(paths)]


def payload_fingerprint(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verified_windows_acceptance(fingerprint):
    path = WIN / 'startup-acceptance.json'
    if path.is_file():
        report = json.loads(path.read_text(encoding='utf-8'))
        if report.get('success') is True and report.get('tested_payload_sha256') == fingerprint:
            return report
    return None


def verified_functional_acceptance(fingerprint):
    path = WIN / 'functional-acceptance.json'
    if path.is_file():
        report = json.loads(path.read_text(encoding='utf-8'))
        if report.get('tested_checks_passed') is True and report.get('tested_payload_sha256') == fingerprint:
            return report
    return None


def manifest():
    print('[manifest] Hashing all deliverable files.', flush=True)
    files = payload_entries()
    fingerprint = payload_fingerprint(files)
    acceptance = verified_windows_acceptance(fingerprint)
    functional = verified_functional_acceptance(fingerprint)
    for path in [WIN / name for name in ['README.txt', 'validation.json', 'startup-acceptance.json', 'functional-acceptance.json'] if (WIN / name).is_file()]:
        files.append({'path': path.relative_to(WIN).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
    files.sort(key=lambda entry: entry['path'])
    report = {'format': 1, 'platform': 'windows-x86_64', 'python': '3.10.20', 'cuda': '12.8',
              'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'total_bytes': sum(f['bytes'] for f in files), 'files': files,
              'payload_sha256': fingerprint,
              'windows_launch_acceptance_passed': bool(acceptance),
              'windows_cpu_functional_acceptance_passed': bool(functional and functional.get('windows_cpu', {}).get('success')),
              'linux_gpu_training_acceptance_passed': bool(functional and functional.get('linux_gpu', {}).get('success')),
              'windows_gpu_training_acceptance_passed': False,
              'windows_acceptance': 'Windows 11 CPU synthesis/ASR and Linux GPU training passed; Windows GPU training pending' if functional else 'Windows 11 launch and dependency checks passed; synthesis and GPU training pending' if acceptance else 'pending Windows launch, dependency, synthesis and training checks',
              'upstream_archives': [PYTHON, FFMPEG, MSVC]}
    write_json(WIN / 'manifest.json', report)
    print(f"[manifest] {len(files)} files; {report['total_bytes'] / 1024 ** 3:.2f} GiB.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['all', 'payload', 'frontend', 'runtime', 'trim', 'manifest'], default='all')
    parser.add_argument('--skip-frontend-build', action='store_true')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    if args.stage == 'all':
        prepare(REPO, PACKAGES)
        subprocess.run(['python3', str(BUILD / 'build_exe.py')], check=True)
    if args.stage in {'all', 'payload'}:
        payload()
    if args.stage in {'all', 'frontend'}:
        frontend(build=not args.skip_frontend_build)
    if args.stage in {'all', 'runtime'}:
        runtime()
    if args.stage in {'all', 'payload', 'runtime', 'trim'}:
        trim()
    if args.stage in {'all', 'manifest'}:
        manifest()


if __name__ == '__main__':
    main()
