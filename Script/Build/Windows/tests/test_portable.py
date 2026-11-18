"""Tests of distribution boundaries and process ownership, runnable on Linux."""
import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

BUILD = Path(__file__).resolve().parents[1]
WIN = Path(__file__).resolve().parents[4] / 'win'
sys.path[:0] = [str(WIN), str(BUILD)]
import launcher
import frontend_server
from assemble import safe_target, relocate_role_metadata
from dependencies import target_requirements, wheel_score


class PortableTests(unittest.TestCase):
    def test_gateway_http_success_cannot_hide_a_failed_service(self):
        with self.assertRaisesRegex(RuntimeError, 'inference.*DLL'):
            launcher.validate_gateway_health({'gateway_status': 'healthy', 'healthy_services': 1, 'total_services': 2,
                'services': {'audio_slice': {'status': 'available'}, 'inference': {'status': 'load_error', 'error': 'missing DLL'}}})
        launcher.validate_gateway_health({'gateway_status': 'healthy', 'healthy_services': 1, 'total_services': 1,
                                         'services': {'inference': {'status': 'available'}}})
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            launcher.validate_gateway_health({'gateway_status': 'healthy'})

    def test_model_paths_relocate_from_linux_and_windows_and_clear_missing_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / 'Resources/Model/世界/角色/v5turbo/GPT/model.ckpt'
            model.parent.mkdir(parents=True)
            model.touch()
            relative = model.relative_to(root).as_posix()
            for path in ['/home/server/project/' + relative, 'D:\\old\\project\\' + relative.replace('/', '\\')]:
                actual = relocate_role_metadata({'gpt_model_path': path, 'sov_model_path': 'D:\\missing.pth', 'gpt_model_id': 123}, root)
                self.assertEqual(actual['gpt_model_path'], relative)
                self.assertIsNone(actual['sov_model_path'])
                self.assertIsNone(actual['gpt_model_id'])

    def test_windows_wheel_selection_rejects_foreign_architecture(self):
        self.assertIsNotNone(wheel_score('torch-2.11.0+cu128-cp310-cp310-win_amd64.whl'))
        self.assertIsNotNone(wheel_score('tokenizers-0.21.4-cp39-abi3-win_amd64.whl'))
        self.assertIsNone(wheel_score('torch-2.11.0-cp310-cp310-manylinux_2_28_x86_64.whl'))
        self.assertIsNone(wheel_score('torch-2.11.0-cp311-cp311-win_amd64.whl'))
        self.assertIsNone(wheel_score('torch-2.11.0-cp310-cp310-win_arm64.whl'))

    def test_requirements_use_target_not_build_host_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'requirements.txt'
            file.write_text('windows-only==1; sys_platform == "win32"\nlinux-only==1; sys_platform == "linux"\npy310-only==1; python_version == "3.10"\n')
            names = {r.name for r in target_requirements(file)}
            self.assertEqual(names, {'windows-only', 'py310-only'})

    def test_archive_cannot_escape_or_overwrite_host_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(safe_target(root, '模型/role.json'), root / '模型/role.json')
            for name in ['../escape.txt', '/etc/passwd', 'foo/../../escape.txt']:
                with self.assertRaises(ValueError):
                    safe_target(root, name)

    def test_invalid_config_cannot_bind_network_or_share_a_port(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            config = {'host': '127.0.0.1', 'backend_port': 40302, 'frontend_port': 40031}
            for update in [{'host': '0.0.0.0'}, {'backend_port': 0}, {'backend_port': True}, {'frontend_port': 40302}]:
                path.write_text(json.dumps(dict(config, **update)))
                with self.assertRaises(ValueError):
                    launcher.load_config(path)

    def test_startup_detects_occupied_port_without_killing_owner(self):
        with socket.socket() as owner:
            owner.bind(('127.0.0.1', 0))
            owner.listen()
            self.assertFalse(launcher.port_is_free('127.0.0.1', owner.getsockname()[1]))
            self.assertGreater(owner.fileno(), 0)

    def test_http_readiness_process_exit_and_owned_cleanup(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
        try:
            handler = lambda *args, **kwargs: frontend_server.Handler(*args, directory=str(WIN / 'app/Code/GptSov_Front/dist'), **kwargs)
            with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                address = f'http://127.0.0.1:{server.server_port}'
                launcher.wait_for_http(address + '/', child, 2)
                frontend_server.Handler.backend_port = 54321
                with urlopen(address + '/mon-config.js') as response:
                    self.assertIn(b'54321', response.read())
                    self.assertEqual(response.headers['Content-Type'], 'application/javascript; charset=utf-8')
                with urlopen(address + '/training/deep/link') as response:
                    self.assertIn(b'<div id="root">', response.read())
                server.shutdown()
                thread.join(timeout=2)
        finally:
            launcher.stop_process(child)
        self.assertIsNotNone(child.poll())
        with self.assertRaisesRegex(RuntimeError, 'exited'):
            launcher.wait_for_http('http://127.0.0.1:1/health', child, .1)

    def test_stop_targets_session_token_not_arbitrary_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'session.json').write_text(json.dumps({'id': 'owned-session-token', 'pid': 1}))
            self.assertEqual(launcher.request_stop(path), 0)
            self.assertEqual((path / 'stop-request').read_text(), 'owned-session-token')

    def test_offline_html_references_local_assets(self):
        html = (WIN / 'app/Code/GptSov_Front/dist/index.html').read_text()
        self.assertNotIn('https://cdn.tailwindcss.com', html)
        self.assertNotIn('fonts.googleapis.com', html)
        self.assertNotIn('type="importmap"', html)
        self.assertIn('/mon-config.js', html)
        css = WIN / 'app/Code/GptSov_Front/dist/assets/tailwind.css'
        self.assertIn('.flex{display:flex}', css.read_text())


if __name__ == '__main__':
    unittest.main()
