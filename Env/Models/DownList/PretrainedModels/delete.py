#!/usr/bin/env python3
import os
import shutil
import sys

_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)

from common import assume_yes, glyph_bad, glyph_ok, load_env_file
from module_config import CONFIG

PROJECT_ROOT, ENV_DIR = load_env_file()


def get_target_path():
    rel_path = os.environ.get(CONFIG["env_var"], CONFIG["default_path"])
    return os.path.join(PROJECT_ROOT, rel_path)


def iter_managed_paths():
    base_path = get_target_path()
    if CONFIG.get("install_mode") == "root_items":
        for name in CONFIG.get("managed_items", []):
            yield os.path.join(base_path, name)
    else:
        yield base_path


def remove_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def delete():
    managed_paths = [path for path in iter_managed_paths() if os.path.exists(path)]

    print("=" * 50)
    print(f"[删除] {CONFIG['name']}")
    print("=" * 50)
    print(f"  根路径: {get_target_path()}")
    print()

    if not managed_paths:
        print("  [!] 文件不存在，无需删除")
        print("=" * 50)
        print(f"[结果] {glyph_ok()} 无需删除")
        return

    if not assume_yes():
        confirm = input("确认删除该模块管理的模型文件? (yes/no): ")
        if confirm.lower() != "yes":
            print("=" * 50)
            print("  [取消] 删除操作已取消")
            return

    failed = []
    for path in managed_paths:
        try:
            remove_path(path)
            print(f"  [{glyph_ok()}] 已删除 {os.path.relpath(path, PROJECT_ROOT)}")
        except Exception as exc:
            failed.append((path, exc))
            print(f"  [{glyph_bad()}] 删除失败 {os.path.relpath(path, PROJECT_ROOT)}: {exc}")

    print("=" * 50)
    if failed:
        print(f"[结果] {glyph_bad()} 部分文件删除失败")
        sys.exit(1)

    print(f"[结果] {glyph_ok()} 删除完成")


if __name__ == "__main__":
    delete()
