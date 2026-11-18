"""Windows acceptance checks. No training or inference task is launched."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def inspect(*, quick=False) -> dict:
    report = {'platform': platform.platform(), 'python': platform.python_version(),
              'architecture': platform.machine(), 'errors': [], 'warnings': []}
    if sys.platform != 'win32' or platform.machine().lower() not in {'amd64', 'x86_64'}:
        report['errors'].append('Requires Windows x64.')
    if sys.version_info[:2] != (3, 10):
        report['errors'].append('The bundled runtime must be CPython 3.10.')
    if sys.platform == 'win32':
        import ctypes
        for library in ['msvcp140.dll', 'msvcp140_1.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']:
            try:
                ctypes.WinDLL(library)
            except OSError as exc:
                report['errors'].append(f'Microsoft C++ runtime missing or damaged: {library}. Restore runtime files or install the official Visual C++ x64 Redistributable. {exc}')
    for name in ['torch', 'torchaudio', 'torchcodec', 'transformers', 'fastapi', 'funasr', 'faster_whisper', 'onnxruntime']:
        if importlib.util.find_spec(name) is None:
            report['errors'].append('Missing Python package: ' + name)
    binary = ROOT / 'Tool/bin/ffmpeg.exe'
    if not binary.is_file():
        report['errors'].append('Missing FFmpeg Windows runtime.')
    for prefix in ['avcodec-', 'avformat-', 'avutil-', 'swresample-', 'swscale-']:
        if not list((ROOT / 'Tool/bin').glob(prefix + '*.dll')):
            report['errors'].append('Missing FFmpeg DLL: ' + prefix)
    pretrained = ROOT / 'app/GPT_SoVITS/pretrained_models'
    for relative in ['chinese-roberta-wwm-ext-large/config.json', 'chinese-hubert-base/config.json', 's1v3.ckpt', 'gsv-v5-pretrained/vocoder.pth']:
        if not (pretrained / relative).is_file():
            report['errors'].append('Missing model: ' + relative)
    nano = ROOT / 'app/tools/asr/models/Fun-ASR-Nano-2512'
    for relative in ['config.yaml', 'configuration.json', 'model.pt', 'multilingual.tiktoken',
                     'Qwen3-0.6B/config.json', 'Qwen3-0.6B/tokenizer.json', 'Qwen3-0.6B/tokenizer_config.json']:
        if not (nano / relative).is_file():
            report['errors'].append('Missing Fun-ASR-Nano model file: ' + relative)
    if not quick and not report['errors']:
        try:
            import torch
            report.update(torch=torch.__version__, cuda=torch.version.cuda, cuda_available=torch.cuda.is_available())
            if torch.cuda.is_available():
                report['gpu'] = torch.cuda.get_device_name(0)
                report['gpu_memory_gib'] = round(torch.cuda.get_device_properties(0).total_memory / 1024 ** 3, 2)
                # Exercise allocation and a small CUDA kernel, then release it.
                result = (torch.ones(8, device='cuda') * 2).sum().item()
                if result != 16:
                    raise RuntimeError('CUDA calculation returned an unexpected result')
            else:
                report['warnings'].append('CUDA is unavailable. CPU inference can be used; GPU training requires an NVIDIA driver and sufficient VRAM.')
            from Code.runtime_env import ensure_audio_runtime
            ensure_audio_runtime(ROOT / 'app', strict=True, verify_torchcodec=True)
            import onnxruntime
            report['onnx_providers'] = onnxruntime.get_available_providers()
            result = subprocess.run([str(binary), '-version'], capture_output=True, text=True, check=True)
            report['ffmpeg'] = result.stdout.splitlines()[0]
            import tkinter
            report['tkinter'] = tkinter.TkVersion
        except Exception as exc:
            report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['success'] = not report['errors']
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args(argv)
    root_app = ROOT / 'app'
    sys.path.insert(0, str(root_app))
    os.environ['PATH'] = str(ROOT / 'Tool/bin') + os.pathsep + os.environ.get('PATH', '')
    report = inspect(quick=args.quick)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    output = ROOT / 'data' / 'diagnostics.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
