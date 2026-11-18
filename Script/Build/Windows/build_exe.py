"""Build a Windows PE launcher using LLVM, without a Windows Python interpreter."""
from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path


def build(destination: Path) -> None:
    required = ['clang', 'llvm-dlltool', 'lld-link']
    for tool in required:
        if not shutil.which(tool):
            raise RuntimeError(f'Missing build tool: {tool}; use the included Start.cmd instead.')
    source = Path(__file__).with_name('launcher.c')
    with tempfile.TemporaryDirectory(prefix='mongsv-pe-') as tmp:
        tmp = Path(tmp)
        exports = {
            'kernel32': ['GetModuleFileNameW', 'GetFileAttributesW', 'GetCommandLineW', 'CreateProcessW', 'WaitForSingleObject', 'GetExitCodeProcess', 'CloseHandle', 'ExitProcess'],
            'user32': ['MessageBoxW'],
        }
        libraries = []
        for dll, functions in exports.items():
            definition = tmp / f'{dll}.def'
            definition.write_text(f'LIBRARY {dll.upper()}.dll\nEXPORTS\n' + '\n'.join(functions) + '\n')
            lib = tmp / f'{dll}.lib'
            subprocess.run(['llvm-dlltool', '-m', 'i386:x86-64', '-d', str(definition), '-l', str(lib)], check=True)
            libraries.append(str(lib))
        obj = tmp / 'launcher.obj'
        subprocess.run(['clang', '--target=x86_64-pc-windows-msvc', '-O2', '-fno-builtin', '-fno-stack-protector', '-c', str(source), '-o', str(obj)], check=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['lld-link', '/entry:mainCRTStartup', '/subsystem:console', '/nodefaultlib', '/machine:x64', '/dynamicbase', '/nxcompat', f'/out:{destination}', str(obj), *libraries], check=True)


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[3] / 'win/MonGSV.exe')
