#!/usr/bin/env python3
"""
通用模块下载脚本模板

使用方法：
1. 复制此文件到新模块目录
2. 修改 CONFIG 字典中的配置
3. 如需自定义下载逻辑，重写 download() 函数
"""
import os
import sys
import zipfile

# 添加 _template 目录到路径以导入 common
_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)
from common import (
    load_env_file,
    hf_hub_download_with_fallback,
    get_hf_endpoint_candidates,
    prepare_redownload,
)

# 加载环境变量并获取项目根目录
PROJECT_ROOT, ENV_DIR = load_env_file()

# ============================================================
# 配置区域 - 根据实际模块修改
# ============================================================
CONFIG = {
    "name": "模块名称",
    "repo": "huggingface/repo-name",  # HuggingFace 仓库
    "file": "model.zip",  # 要下载的文件名
    "env_var": "ENV_VAR_NAME",  # 环境变量名称
    "default_path": "default/path",  # 默认相对路径
    "extract": True,  # 是否需要解压
}


def get_target_path():
    """从环境变量获取目标路径"""
    rel_path = os.environ.get(CONFIG["env_var"], CONFIG["default_path"])
    return os.path.join(PROJECT_ROOT, rel_path)


def download():
    """下载模块文件"""
    target_path = get_target_path()

    print("=" * 50)
    print(f"[下载] {CONFIG['name']}")
    print("=" * 50)
    print(f"  仓库: {CONFIG['repo']}")
    print(f"  文件: {CONFIG['file']}")
    print(f"  下载到: {os.path.dirname(target_path)}")
    if CONFIG["extract"]:
        print(f"  解压到: {target_path}")
    print(f"  根目录: {PROJECT_ROOT}")
    print(f"  端点: {' -> '.join(get_hf_endpoint_candidates())}")
    print()

    module_dir = os.path.dirname(__file__)
    if not prepare_redownload(module_dir, PROJECT_ROOT, target_path, is_dir=True):
        return

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    try:
        print("  [→] 开始下载...")

        local_path = hf_hub_download_with_fallback(
            repo_id=CONFIG["repo"],
            filename=CONFIG["file"],
            repo_type="model",
        )

        if CONFIG["extract"]:
            print(f"  [*] 解压到: {os.path.dirname(target_path)}")
            with zipfile.ZipFile(local_path, "r") as z:
                z.extractall(os.path.dirname(target_path))
            print(f"  [✓] 解压完成: {target_path}")

        print("=" * 50)
        print("[结果] ✓ 下载完成")
        print(f"[位置] {target_path}")
    except Exception as e:
        print(f"  [!] 下载失败: {e}")
        print("=" * 50)
        print("[结果] ✗ 下载失败")
        sys.exit(1)


if __name__ == "__main__":
    download()
