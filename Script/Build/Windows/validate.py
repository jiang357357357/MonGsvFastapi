"""Static Windows distribution checks. This does not execute Windows binaries."""
from __future__ import annotations
import ast
import json
import re
import struct
import subprocess
import sys
from collections import defaultdict
from email.parser import BytesParser
from pathlib import Path

from dependencies import digest, validate_dependency_metadata, wheel_score
from assemble import payload_entries, payload_fingerprint, verified_windows_acceptance, verified_functional_acceptance
from packaging.utils import canonicalize_name

BUILD = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
WIN = REPO / 'win'
CACHE = REPO / 'Temp/WinBuild'
PACKAGES = CACHE / 'packages'


def pe_info(path: Path) -> dict:
    # Read PE headers only; large CUDA DLLs need not be loaded into RAM.
    with path.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError(f'Not a PE binary: {path}')
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        if stream.read(4) != b'PE\0\0':
            raise ValueError(f'Invalid PE signature: {path}')
        machine, section_count, _, _, _, optional_size, _ = struct.unpack('<HHIIIHH', stream.read(20))
        optional = stream.read(optional_size)
        magic = struct.unpack_from('<H', optional)[0]
        sections = []
        for _ in range(section_count):
            section = stream.read(40)
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from('<IIII', section, 8)
            sections.append((virtual_address, max(virtual_size, raw_size), raw_offset))
        def position(rva):
            for address, size, raw in sections:
                if address <= rva < address + size:
                    return rva - address + raw
            raise ValueError(f'Invalid PE RVA {rva}: {path}')
        imports = []
        directory_offset = 112 if magic == 0x20b else 96
        rva, size = struct.unpack_from('<II', optional, directory_offset + 8)
        if rva:
            descriptor_offset = position(rva)
            for i in range(min(size // 20, 4096)):
                stream.seek(descriptor_offset + i * 20)
                descriptor = struct.unpack('<IIIII', stream.read(20))
                if not any(descriptor):
                    break
                stream.seek(position(descriptor[3]))
                name = bytearray()
                while True:
                    char = stream.read(1)
                    if char in {b'', b'\0'}:
                        break
                    name.extend(char)
                imports.append(name.decode('ascii'))
    return {'machine': hex(machine), 'pe32_plus': magic == 0x20b, 'imports': imports}


def validate() -> dict:
    errors = []
    plan = json.loads((PACKAGES / 'index.json').read_text())
    for item in plan:
        file = PACKAGES / item['filename']
        if not file.is_file() or digest(file) != item['hash'].split(':')[1]:
            errors.append('Missing or damaged dependency: ' + item['filename'])
        if wheel_score(item['filename']) is None:
            errors.append('Incompatible wheel: ' + item['filename'])
    errors += validate_dependency_metadata(PACKAGES, plan)
    nano = WIN / 'app/tools/asr/models/Fun-ASR-Nano-2512'
    provenance = nano / 'source.json'
    nano_checks = []
    if not provenance.is_file():
        errors.append('Missing pinned Fun-ASR-Nano model provenance: ' + str(provenance))
    else:
        source = json.loads(provenance.read_text(encoding='utf-8'))
        if source.get('repo') != 'FunAudioLLM/Fun-ASR-Nano-2512' or source.get('revision') != '272c57b82523ada6fd87095e955f8e29100979ab':
            errors.append('Unexpected Fun-ASR-Nano model revision')
        if not any(entry.get('file') == 'model.pt' and entry.get('sha256') == '55ae0d2fee369f0f11cce0795f6927934ad17cf11b278a7e56a51272074160bb' for entry in source.get('files', [])):
            errors.append('Unexpected Fun-ASR-Nano weight checksum')
        for entry in source.get('files', []):
            file = nano / entry['file']
            valid = file.is_file() and file.stat().st_size == entry['bytes'] and digest(file) == entry['sha256']
            nano_checks.append({'file': entry['file'], 'valid': valid})
            if not valid:
                errors.append('Missing or damaged Fun-ASR-Nano file: ' + entry['file'])
    installed = defaultdict(list)
    for info in (WIN / 'runtime/Lib/site-packages').glob('*.dist-info'):
        metadata = BytesParser().parsebytes((info / 'METADATA').read_bytes())
        installed[canonicalize_name(metadata['Name'])].append(metadata['Version'])
    for item in plan:
        if installed[item['name']] != [item['version']]:
            errors.append(f"Installed metadata differs from lock: {item['name']} {installed[item['name']]}")
    pe = {}
    native = [WIN / 'MonGSV.exe', WIN / 'runtime/python.exe', *list((WIN / 'runtime').rglob('*.dll')),
              *list((WIN / 'runtime/Lib/site-packages').rglob('*.pyd')),
              *list((WIN / 'Tool/bin').glob('*.exe')), *list((WIN / 'Tool/bin').glob('*.dll'))]
    for file in native:
        info = pe_info(file)
        pe[file.relative_to(WIN).as_posix()] = info
        if info['machine'] != '0x8664' or not info['pe32_plus']:
            errors.append('Incompatible native binary: ' + str(file))
        for library in info['imports']:
            if re.fullmatch(r'(?:msvcp140(?:_[a-z0-9_]+)?|vcruntime140(?:_[a-z0-9_]+)?|vcomp140|concrt140)\.dll', library, re.I):
                if not (WIN / 'runtime' / library.lower()).is_file():
                    errors.append(f'Missing app-local C++ runtime: {library} required by {file.relative_to(WIN)}')
    syntax_files = [*list((WIN / 'app').rglob('*.py')), WIN / 'launcher.py', WIN / 'frontend_server.py', WIN / 'diagnose.py']
    for file in syntax_files:
        try:
            # Feature version rejects syntax the actual Python 3.10 cannot parse.
            ast.parse(file.read_text(encoding='utf-8-sig'), filename=str(file), feature_version=(3, 10))
        except (SyntaxError, UnicodeError) as exc:
            errors.append('Python 3.10 syntax: ' + str(exc))
    windows_names = []
    case_names = {}
    for folder in ['app', 'runtime', 'Tool']:
        for file in (WIN / folder).rglob('*'):
            key = file.relative_to(WIN).as_posix().casefold()
            if key in case_names and case_names[key] != str(file):
                errors.append('Windows case collision: ' + str(file))
            case_names[key] = str(file)
            if re.search(r'[<>:"\\|?*]', file.name) or file.name.endswith((' ', '.')):
                windows_names.append(str(file.relative_to(WIN)))
    errors += ['Invalid Windows filename: ' + name for name in windows_names]
    tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(BUILD / 'tests'), '-v'],
                           cwd=REPO, capture_output=True, text=True)
    (CACHE / 'unit-tests.txt').write_text(tests.stdout + tests.stderr, encoding='utf-8')
    if tests.returncode:
        errors.append('Portable launcher unit tests failed; see Temp/WinBuild/unit-tests.txt')
    browser = json.loads((CACHE / 'browser/report.json').read_text())
    catalog = json.loads((CACHE / 'catalog-validation.json').read_text())
    if not browser['success'] or catalog['invalid_paths']:
        errors.append('Frontend or model relocation validation failed')
    fingerprint = payload_fingerprint(payload_entries()) if (WIN / 'startup-acceptance.json').is_file() else None
    acceptance = verified_windows_acceptance(fingerprint) if fingerprint else None
    functional = verified_functional_acceptance(fingerprint) if fingerprint else None
    report = {'static_build_checks_passed': not errors, 'build_platform': sys.platform,
              'windows_launch_acceptance_passed': bool(acceptance),
              'windows_launch_acceptance': acceptance,
              'windows_cpu_functional_acceptance_passed': bool(functional and functional.get('windows_cpu', {}).get('success')),
              'linux_gpu_training_acceptance_passed': bool(functional and functional.get('linux_gpu', {}).get('success')),
              'windows_gpu_training_acceptance_passed': False,
              'functional_acceptance': functional,
              'windows_runtime_acceptance_passed': False,
              'windows_runtime_acceptance_status': 'Windows CPU synthesis/ASR and Linux GPU training passed; Windows GPU training pending' if functional else 'Windows launch and dependency checks passed; synthesis and GPU training pending' if acceptance else 'pending Windows execution of Check.cmd, synthesis and training',
              'wheel_count': len(plan), 'dependency_errors': validate_dependency_metadata(PACKAGES, plan),
              'fun_asr_nano_files': nano_checks,
              'native_binaries_checked': len(pe), 'native_binaries': pe, 'python_source_files_checked': len(syntax_files),
              'unit_tests_passed': tests.returncode == 0, 'browser': browser, 'catalog': catalog,
              'packaging_notes': json.loads((WIN / 'packaging-notes.json').read_text()), 'errors': errors}
    (WIN / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    result = validate()
    print(json.dumps({key: value for key, value in result.items() if key in {
        'static_build_checks_passed', 'wheel_count', 'native_binaries_checked', 'python_source_files_checked', 'errors'}}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['static_build_checks_passed'] else 1)
