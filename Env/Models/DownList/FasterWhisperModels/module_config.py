#!/usr/bin/env python3

CONFIG = {
    "name": "Faster Whisper 模型",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "faster-whisper.zip",
    "env_var": "FASTER_WHISPER_MODELS_PATH",
    "default_path": "tools/asr/models",
    "temp_prefix": "FasterWhisperModels",
    "install_mode": "root_items",
    "strip_single_root": False,
    "managed_items": [
        "faster-whisper-large-v3",
    ],
    "files": [
        "faster-whisper-large-v3/config.json",
        "faster-whisper-large-v3/model.bin",
        "faster-whisper-large-v3/tokenizer.json",
        "faster-whisper-large-v3/preprocessor_config.json",
        "faster-whisper-large-v3/vocabulary.json",
    ],
}
