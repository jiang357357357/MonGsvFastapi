#!/usr/bin/env python3
import os
import sys

# 添加 _template 目录到路径以导入 common
_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)
from common import load_env_file, glyph_ok, glyph_bad

# 加载环境变量并获取项目根目录
PROJECT_ROOT, ENV_DIR = load_env_file()

CONFIG = {
    "name": "中文字音转换模型",
    "env_var": "G2PW_MODEL_PATH",
    "default_path": "GPT_SoVITS/text/G2PWModel",
    "files": ["g2pw.pt", "bert-base-chinese"],
}


def get_target_path():
    """从环境变量获取目标路径"""
    rel_path = os.environ.get(CONFIG["env_var"], CONFIG["default_path"])
    return os.path.join(PROJECT_ROOT, rel_path)

def get_size(path):
    """获取文件或目录大小（MB）"""
    if not os.path.exists(path):
        return 0
    if os.path.isdir(path):
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, dn, fn in os.walk(path)
            for f in fn
        )
        return total / 1024 / 1024
    return os.path.getsize(path) / 1024 / 1024


def check():
    """检查模块是否完整安装"""
    base_path = get_target_path()
    files = CONFIG["files"]

    print("=" * 50)
    print(f"[检查] {CONFIG['name']}")
    print("=" * 50)
    print(f"  路径: {base_path}")
    print()

    all_exist = True
    ok = glyph_ok()
    bad = glyph_bad()
    for f in files:
        file_path = os.path.join(base_path, f)
        if os.path.exists(file_path):
            size = get_size(file_path)
            print(f"  [{ok}] {f} ({size:.1f} MB)")
        else:
            print(f"  [{bad}] {f} - 缺失")
            all_exist = False

    print("=" * 50)
    if all_exist:
        print(f"[结果] {ok} 所有文件检查通过")
        return True
    else:
        print(f"[结果] {bad} 部分文件缺失")
        return False

if __name__ == "__main__":
    sys.exit(0 if check() else 1)
