#!/usr/bin/env python3
"""
配置示例文件

展示不同类型模块的配置方式
"""

# ============================================================
# 示例 1: 标准 ZIP 压缩包模型
# ============================================================
CONFIG_ZIP_MODEL = {
    "name": "核心预训练模型包",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "pretrained_models.zip",
    "env_var": "PRETRAINED_MODELS_PATH",
    "default_path": "GPT_SoVITS/pretrained_models",
    "extract": True,
    "files": [
        "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
        "s2G488k.pth",
        "s2D488k.pth",
        "chinese-roberta-wwm-ext-large",
        "chinese-hubert-base",
    ],
}

# ============================================================
# 示例 2: 单个目录模型
# ============================================================
CONFIG_DIR_MODEL = {
    "name": "中文字音转换模型",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "G2PWModel.zip",
    "env_var": "G2PW_MODEL_PATH",
    "default_path": "GPT_SoVITS/text/G2PWModel",
    "extract": True,
    "files": [
        "config.json",
        "pytorch_model.bin",
        "vocab.txt",
    ],
}

# ============================================================
# 示例 3: 多文件数据包
# ============================================================
CONFIG_DATA_PACKAGE = {
    "name": "NLTK 文本处理数据包",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "nltk_data.zip",
    "env_var": "NLTK_DATA_PATH",
    "default_path": "nltk_data",
    "extract": True,
    "files": [
        "corpora",
        "tokenizers",
    ],
}

# ============================================================
# 示例 4: 权重文件集合
# ============================================================
CONFIG_WEIGHTS = {
    "name": "UVR5 人声伴奏分离模型",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "uvr5_weights.zip",
    "env_var": "UVR5_WEIGHTS_PATH",
    "default_path": "tools/uvr5/uvr5_weights",
    "extract": True,
    "files": [
        "HP2-人声vocals+非人声instrumentals.pth",
        "HP5-主旋律人声vocals+其他instrumentals.pth",
    ],
}

# ============================================================
# 示例 5: 不需要解压的单文件
# ============================================================
CONFIG_SINGLE_FILE = {
    "name": "单个模型文件",
    "repo": "username/repo-name",
    "file": "model.pth",
    "env_var": "MODEL_FILE_PATH",
    "default_path": "models/model.pth",
    "extract": False,  # 不解压
    "files": [
        "model.pth",
    ],
}
