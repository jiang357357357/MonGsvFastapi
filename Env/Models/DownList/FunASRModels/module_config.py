#!/usr/bin/env python3

CONFIG = {
    "name": "FunASR 中文模型",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "funasr.zip",
    "env_var": "FUNASR_MODELS_PATH",
    "default_path": "tools/asr/models",
    "temp_prefix": "FunASRModels",
    "install_mode": "root_items",
    "strip_single_root": True,
    "managed_items": [
        "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    ],
    "files": [
        "punc_ct-transformer_zh-cn-common-vocab272727-pytorch/configuration.json",
        "punc_ct-transformer_zh-cn-common-vocab272727-pytorch/model.pt",
        "speech_fsmn_vad_zh-cn-16k-common-pytorch/configuration.json",
        "speech_fsmn_vad_zh-cn-16k-common-pytorch/model.pt",
        "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/configuration.json",
        "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt",
    ],
}
