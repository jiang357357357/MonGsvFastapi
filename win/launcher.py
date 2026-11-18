"""Supervise the portable frontend/backend and stop their process trees together."""
from __future__ import annotations
import argparse
import atexit
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
APP = ROOT / 'app'
STATE = ROOT / 'data' / 'launcher'


def load_config(path: Path = ROOT / 'config.json') -> dict:
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if config.get('host') not in {'127.0.0.1', 'localhost'}:
        raise ValueError('This local edition must bind to 127.0.0.1 or localhost.')
    for key in ['backend_port', 'frontend_port']:
        if type(config.get(key)) is not int or not 1 <= config[key] <= 65535:
            raise ValueError(f'Invalid {key}; expected an integer from 1 to 65535.')
    if config['backend_port'] == config['frontend_port']:
        raise ValueError('Frontend and backend ports must be different.')
    if not 1 <= float(config.get('startup_timeout', 180)) <= 1800:
        raise ValueError('startup_timeout must be between 1 and 1800 seconds.')
    return config


def environment(root: Path = ROOT) -> dict:
    env = os.environ.copy()
    app = root / 'app'
    env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONNOUSERSITE='1',
               PYTHONUNBUFFERED='1', MON_WORKSPACE_ROOT=str(app), MON_GSV_ENV='production',
               NLTK_DATA=str(root / 'runtime' / 'nltk_data'),
               HF_HOME=str(app / 'Data' / 'Cache' / 'huggingface'))
    env['PYTHONPATH'] = str(app)
    env['PATH'] = os.pathsep.join([str(root / 'Tool' / 'bin'), str(root / 'runtime'),
                                  str(root / 'runtime' / 'Scripts'), env.get('PATH', '')])
    return env


def port_is_free(host: str, port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def acquire_single_instance() -> bool:
    """Windows owns the lock lifetime, including forced console closure."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    identity = hashlib.sha256(os.path.normcase(str(ROOT)).encode('utf-8')).hexdigest()[:32]
    ctypes.set_last_error(0)
    handle = kernel.CreateMutexW(None, False, 'Local\\MonGSV.' + identity)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel.CloseHandle(handle)
        return False
    atexit.register(kernel.CloseHandle, handle)
    return True


def wait_for_http(url: str, process: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Service exited before it was ready: code={process.returncode}')
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            pass
        time.sleep(.2)
    raise TimeoutError(f'Service did not become ready within {timeout}s: {url}')


def validate_gateway_health(health: dict) -> None:
    services = health.get('services', {})
    failures = [f"{name}: {details.get('error', details['status'])}"
                for name, details in services.items() if details.get('status') in {'error', 'load_error'}]
    if failures:
        raise RuntimeError('Backend service initialization failed: ' + '; '.join(failures))
    if not services or health.get('healthy_services') != health.get('total_services'):
        raise RuntimeError('Backend health report is incomplete.')


class WindowsJob:
    """Closing the launcher also terminates backend training grandchildren."""
    def __init__(self):
        self.handle = None
        if os.name != 'nt':
            return
        import ctypes
        from ctypes import wintypes as w
        class BASIC(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', w.DWORD), ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t),
                        ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ['read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes']]
        class LIMITS(ctypes.Structure):
            _fields_ = [('basic', BASIC), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        limits = LIMITS()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def attach(self, process: subprocess.Popen) -> None:
        if self.handle and not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            import ctypes
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.kill()
        process.wait(timeout=5)


def request_stop(state_dir: Path = STATE) -> int:
    file = state_dir / 'session.json'
    if not file.is_file():
        print('MonGSV is not running.')
        return 0
    state = json.loads(file.read_text(encoding='utf-8'))
    (state_dir / 'stop-request').write_text(state['id'], encoding='ascii')
    print('Stop requested. The launcher will close its services and training processes.')
    return 0


def pump(stream, label: str, logfile) -> None:
    for line in iter(stream.readline, ''):
        text = f'[{label}] {line.rstrip()}'
        print(text, flush=True)
        logfile.write(text + '\n')
        logfile.flush()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='MonGSV portable Windows launcher')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    STATE.mkdir(parents=True, exist_ok=True)
    if args.stop:
        return request_stop()
    if args.check:
        return subprocess.call([sys.executable, '-s', str(ROOT / 'diagnose.py')], env=environment())
    if sys.platform != 'win32':
        print('This distribution contains Windows binaries. Run MonGSV.exe on Windows x64.')
        return 1
    if not acquire_single_instance():
        print('MonGSV is already running from this folder.')
        return 1
    config = load_config()
    for name in ['backend', 'frontend']:
        if not port_is_free(config['host'], config[name + '_port']):
            print(f"Port {config[name + '_port']} is already in use. Close the other program or edit config.json.")
            return 1
    required = [APP / 'Code/FastApi/Base/Gateway/run_unified_gateway.py', APP / 'Code/GptSov_Front/dist/index.html']
    if not all(path.is_file() for path in required):
        print('Application files are incomplete. Copy the complete win folder.')
        return 1
    print('MonGSV Windows local edition. Logs: data/launcher/console.log\n', flush=True)
    print('Loading local audio libraries. The first start on a fresh Windows installation can take several minutes.\n', flush=True)
    check = subprocess.run([sys.executable, '-s', str(ROOT / 'diagnose.py'), '--quick'], env=environment(), check=False)
    if check.returncode:
        return check.returncode
    children = []
    job = WindowsJob()
    identity = uuid.uuid4().hex
    statefile = STATE / 'session.json'
    stopfile = STATE / 'stop-request'
    logfile = (STATE / 'console.log').open('a', encoding='utf-8', buffering=1)
    readers = []
    commands = [
        ('backend', [sys.executable, str(APP / 'Code/FastApi/Base/Gateway/run_unified_gateway.py'),
                     '--host', config['host'], '--port', str(config['backend_port']), '--no-reload']),
        ('frontend', [sys.executable, str(ROOT / 'frontend_server.py'), '--port', str(config['frontend_port']),
                      '--backend-port', str(config['backend_port'])]),
    ]
    try:
        for name, command in commands:
            process = subprocess.Popen(command, cwd=APP, env=environment(), stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            children.append(process)
            job.attach(process)
            reader = threading.Thread(target=pump, args=(process.stdout, name, logfile), daemon=True)
            reader.start()
            readers.append(reader)
        statefile.write_text(json.dumps({'id': identity, 'pid': os.getpid(), 'root': str(ROOT)}), encoding='utf-8')
        backend_url = f"http://127.0.0.1:{config['backend_port']}"
        frontend_url = f"http://127.0.0.1:{config['frontend_port']}/"
        wait_for_http(backend_url + '/health', children[0], config['startup_timeout'])
        with urlopen(backend_url + '/health', timeout=10) as response:
            validate_gateway_health(json.load(response))
        wait_for_http(frontend_url, children[1], 20)
        print(f'\nReady: {frontend_url}\nPress Ctrl+C or run Stop.cmd to stop.\n', flush=True)
        if config.get('open_browser', True) and not args.no_browser:
            webbrowser.open(frontend_url)
        while True:
            if stopfile.is_file() and stopfile.read_text(encoding='ascii') == identity:
                return 0
            for process in children:
                if process.poll() is not None:
                    raise RuntimeError(f'A service exited unexpectedly: code={process.returncode}')
            time.sleep(.3)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f'\nERROR: {exc}\nDetails: {STATE / "console.log"}', file=sys.stderr)
        return 1
    finally:
        for process in reversed(children):
            stop_process(process)
        job.close()
        for reader in readers:
            reader.join(timeout=5)
        if not any(reader.is_alive() for reader in readers):
            logfile.close()
        for file in [statefile, stopfile]:
            if file.is_file():
                file.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
