#!/usr/bin/env python3
"""
G2PWModel 下载脚本
功能：仅下载模型文件到临时目录，不解压
"""
import os
import sys
import tempfile
import argparse

# 添加 _template 目录到路径
_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)
from common import load_env_file, hf_hub_download_with_fallback, get_hf_endpoint_candidates

# 加载环境变量并获取项目根目录
PROJECT_ROOT, ENV_DIR = load_env_file()

CONFIG = {
    "name": "中文字音转换模型",
    "repo": "XXXXRT/GPT-SoVITS-Pretrained",
    "file": "G2PWModel.zip"
}


def download(output_path=None, skip_existing=False):
    """下载模型文件"""
    # 确定输出路径
    if output_path is None:
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"G2PWModel_{os.urandom(4).hex()}.zip")
    
    # 检查是否已存在
    if skip_existing and os.path.exists(output_path):
        print(f"文件已存在，跳过下载: {output_path}")
        return output_path
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("=" * 50)
    print(f"[下载] {CONFIG['name']}")
    print("=" * 50)
    print(f"  仓库: {CONFIG['repo']}")
    print(f"  文件: {CONFIG['file']}")
    print(f"  端点: {' -> '.join(get_hf_endpoint_candidates())}")
    print(f"  保存路径: {output_path}")
    print()
    
    try:
        print("  [→] 开始下载...")
        
        local_path = hf_hub_download_with_fallback(
            repo_id=CONFIG["repo"],
            filename=CONFIG["file"],
            repo_type="model",
        )
        
        # 复制到指定输出路径
        import shutil
        shutil.copy2(local_path, output_path)
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print()
        print("=" * 50)
        print("[结果] ✓ 下载完成")
        print(f"  文件大小: {file_size:.2f} MB")
        print(f"  保存位置: {output_path}")
        print("=" * 50)
        print()
        print("提示: 使用 install.py 安装此文件")
        print(f'  示例: python install.py "{output_path}"')
        print()
        
        return output_path
        
    except Exception as e:
        print(f"  [!] 下载失败: {e}")
        print("=" * 50)
        print("[结果] × 下载失败")
        # 清理失败的文件
        if os.path.exists(output_path):
            os.remove(output_path)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载 G2PWModel 模型")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--skip-existing", action="store_true", help="如果文件已存在则跳过")
    args = parser.parse_args()
    
    download(output_path=args.output, skip_existing=args.skip_existing)
