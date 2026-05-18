#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import tempfile

_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)

from common import (
    get_hf_endpoint_candidates,
    hf_hub_download_with_fallback,
    load_env_file,
)
from module_config import CONFIG

PROJECT_ROOT, ENV_DIR = load_env_file()


def get_target_path():
    rel_path = os.environ.get(CONFIG["env_var"], CONFIG["default_path"])
    return os.path.join(PROJECT_ROOT, rel_path)


def get_default_output_path():
    return os.path.join(
        tempfile.gettempdir(),
        f"{CONFIG['temp_prefix']}_{os.urandom(4).hex()}.zip",
    )


def download(output_path=None, skip_existing=False):
    output_path = output_path or get_default_output_path()

    if skip_existing and os.path.exists(output_path):
        print(f"文件已存在，跳过下载: {output_path}")
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("=" * 50)
    print(f"[下载] {CONFIG['name']}")
    print("=" * 50)
    print(f"  仓库: {CONFIG['repo']}")
    print(f"  文件: {CONFIG['file']}")
    print(f"  端点: {' -> '.join(get_hf_endpoint_candidates())}")
    print(f"  保存位置: {output_path}")
    print(f"  安装目标: {get_target_path()}")
    print()

    try:
        local_path = hf_hub_download_with_fallback(
            repo_id=CONFIG["repo"],
            filename=CONFIG["file"],
            repo_type="model",
        )
        shutil.copy2(local_path, output_path)
        file_size = os.path.getsize(output_path) / 1024 / 1024

        print("=" * 50)
        print("[结果] ✓ 下载完成")
        print(f"  文件大小: {file_size:.2f} MB")
        print(f"  保存位置: {output_path}")
        print("=" * 50)
        print(f'提示: 使用 install.py 安装此文件，例如: python install.py "{output_path}"')
        return output_path
    except Exception:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"下载 {CONFIG['name']}")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--skip-existing", action="store_true", help="如果文件已存在则跳过")
    args = parser.parse_args()
    download(output_path=args.output, skip_existing=args.skip_existing)
