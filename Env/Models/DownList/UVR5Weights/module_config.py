#!/usr/bin/env python3

CONFIG = {
    "name": "UVR5 权重包",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "uvr5_weights.zip",
    "env_var": "UVR5_WEIGHTS_PATH",
    "default_path": "tools/uvr5/uvr5_weights",
    "temp_prefix": "UVR5Weights",
    "install_mode": "root_items",
    "strip_single_root": True,
    "managed_items": [
        "HP2-人声vocals+非人声instrumentals.pth",
        "HP5-主旋律人声vocals+其他instrumentals.pth",
        "onnx_dereverb_By_FoxJoy",
    ],
    "files": [
        "HP2-人声vocals+非人声instrumentals.pth",
        "HP5-主旋律人声vocals+其他instrumentals.pth",
        "onnx_dereverb_By_FoxJoy",
    ],
}
