#!/usr/bin/env python3
import os
import sys

_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)

from common import glyph_bad, glyph_ok, load_env_file
from module_config import CONFIG

PROJECT_ROOT, ENV_DIR = load_env_file()


def get_target_path():
    rel_path = os.environ.get(CONFIG["env_var"], CONFIG["default_path"])
    return os.path.join(PROJECT_ROOT, rel_path)


def get_size(path):
    if not os.path.exists(path):
        return 0
    if os.path.isdir(path):
        total = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(path)
            for filename in filenames
        )
        return total / 1024 / 1024
    return os.path.getsize(path) / 1024 / 1024


def check():
    base_path = get_target_path()
    ok = glyph_ok()
    bad = glyph_bad()
    all_exist = True

    print("=" * 50)
    print(f"[检查] {CONFIG['name']}")
    print("=" * 50)
    print(f"  路径: {base_path}")
    print()

    for rel_path in CONFIG["files"]:
        full_path = os.path.join(base_path, rel_path)
        if os.path.exists(full_path):
            print(f"  [{ok}] {rel_path} ({get_size(full_path):.1f} MB)")
        else:
            print(f"  [{bad}] {rel_path} - 缺失")
            all_exist = False

    print("=" * 50)
    if all_exist:
        print(f"[结果] {ok} 所有文件检查通过")
        return True

    print(f"[结果] {bad} 部分文件缺失")
    return False


if __name__ == "__main__":
    sys.exit(0 if check() else 1)
