"""Portable process bootstrap; imported by the bundled CPython, including workers."""
import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[2]
_ROOT = _RUNTIME.parent
_APP = _ROOT / 'app'
_DLL_HANDLES = []
for _path in [_APP, _APP / 'GPT_SoVITS']:
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
os.environ.setdefault('PYTHONUTF8', '1')
os.environ.setdefault('MON_WORKSPACE_ROOT', str(_APP))
os.environ.setdefault('NLTK_DATA', str(_RUNTIME / 'nltk_data'))
os.environ.setdefault('HF_HOME', str(_APP / 'Data/Cache/huggingface'))
os.environ.setdefault('G2PW', '0')
os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
_directories = [_ROOT / 'Tool/bin', _RUNTIME, _RUNTIME / 'Scripts',
                _RUNTIME / 'Lib/site-packages/torch/lib',
                *sorted((_RUNTIME / 'Lib/site-packages/nvidia').glob('*/bin'))]
os.environ['PATH'] = os.pathsep.join([str(p) for p in _directories if p.is_dir()] + [os.environ.get('PATH', '')])
if os.name == 'nt':
    for _directory in _directories:
        if _directory.is_dir():
            _DLL_HANDLES.append(os.add_dll_directory(str(_directory)))
