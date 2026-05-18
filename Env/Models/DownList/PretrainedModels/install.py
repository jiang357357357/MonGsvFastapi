#!/usr/bin/env python3
import argparse
import glob
import os
import shutil
import sys
import tempfile
import zipfile

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


def get_latest_download():
    pattern = os.path.join(tempfile.gettempdir(), f"{CONFIG['temp_prefix']}_*.zip")
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def remove_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def install_root_items(temp_dir, target_path):
    sources = [os.path.join(temp_dir, name) for name in os.listdir(temp_dir)]
    if CONFIG.get("strip_single_root") and len(sources) == 1 and os.path.isdir(sources[0]):
        single_root = sources[0]
        sources = [os.path.join(single_root, name) for name in os.listdir(single_root)]

    os.makedirs(target_path, exist_ok=True)
    for source in sources:
        destination = os.path.join(target_path, os.path.basename(source))
        if os.path.exists(destination):
            remove_path(destination)
        shutil.move(source, destination)


def install(source_file=None, force=False):
    source_file = source_file or get_latest_download()
    if not source_file:
        print("错误: 未找到下载文件，请先运行 download.py")
        sys.exit(1)
    if not os.path.exists(source_file):
        print(f"错误: 源文件不存在: {source_file}")
        sys.exit(1)

    target_path = get_target_path()
    file_size = os.path.getsize(source_file) / 1024 / 1024

    print("=" * 50)
    print(f"[安装] {CONFIG['name']}")
    print("=" * 50)
    print(f"  源文件: {source_file}")
    print(f"  文件大小: {file_size:.2f} MB")
    print(f"  目标路径: {target_path}")
    print()

    temp_dir = tempfile.mkdtemp(prefix=f"{CONFIG['temp_prefix']}_install_")
    try:
        with zipfile.ZipFile(source_file, "r") as zip_file:
            zip_file.extractall(temp_dir)

        install_root_items(temp_dir, target_path)

        missing = [
            rel_path
            for rel_path in CONFIG["files"]
            if not os.path.exists(os.path.join(target_path, rel_path))
        ]
        if missing:
            print(f"[结果] {glyph_bad()} 安装不完整，缺失以下文件:")
            for rel_path in missing:
                print(f"  - {rel_path}")
            sys.exit(1)

        installed_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(target_path)
            for filename in filenames
        ) / 1024 / 1024
        print("=" * 50)
        print(f"[结果] {glyph_ok()} 安装成功")
        print(f"  安装路径: {target_path}")
        print(f"  占用空间: {installed_size:.2f} MB")
        print("=" * 50)
    except Exception as exc:
        print("=" * 50)
        print(f"[结果] {glyph_bad()} 安装失败")
        print(f"  错误信息: {exc}")
        print("=" * 50)
        sys.exit(1)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"安装 {CONFIG['name']}")
    parser.add_argument("source_file", nargs="?", help="要安装的 zip 文件路径")
    parser.add_argument("--force", "-f", action="store_true", help="保留兼容参数")
    args = parser.parse_args()
    install(source_file=args.source_file, force=args.force)
