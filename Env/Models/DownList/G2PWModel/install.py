#!/usr/bin/env python3
"""
G2PWModel 安装脚本
功能：解压已下载的模型文件到目标目录
"""
import glob
import os
import sys
import tempfile
import zipfile
import shutil
import argparse

# 添加 _template 目录到路径
_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)
from common import load_env_file

# 加载环境变量并获取项目根目录
PROJECT_ROOT, ENV_DIR = load_env_file()


def get_latest_download():
    """在临时目录中找到最近下载的 G2PWModel zip 文件"""
    pattern = os.path.join(tempfile.gettempdir(), "G2PWModel_*.zip")
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def get_target_path():
    """从环境变量获取目标路径"""
    rel_path = os.environ.get('G2PW_MODEL_PATH', 'GPT_SoVITS/text/G2PWModel')
    return os.path.join(PROJECT_ROOT, rel_path)


def install(source_file=None, force=False):
    """安装模型文件"""
    source_file = source_file or get_latest_download()
    if not source_file:
        print("错误: 未找到下载文件，请先运行 download.py")
        sys.exit(1)
    if not os.path.exists(source_file):
        print(f"错误: 源文件不存在: {source_file}")
        sys.exit(1)
    
    file_size = os.path.getsize(source_file) / (1024 * 1024)
    target_path = get_target_path()
    
    print("=" * 50)
    print("[安装] G2PWModel 模型")
    print("=" * 50)
    print(f"  源文件: {source_file}")
    print(f"  文件大小: {file_size:.2f} MB")
    print(f"  目标路径: {target_path}")
    print()
    
    # 检查目标路径
    if os.path.exists(target_path):
        if force:
            print("目标路径已存在，强制删除...")
            shutil.rmtree(target_path)
        else:
            response = input("目标路径已存在，是否删除并重新安装? (y/N): ")
            if response.lower() == 'y':
                print("删除旧文件...")
                shutil.rmtree(target_path)
            else:
                print("安装已取消")
                return
    
    # 创建临时目录
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="G2PWModel_install_")
    
    try:
        # 解压文件
        print("解压文件...")
        with zipfile.ZipFile(source_file, 'r') as z:
            z.extractall(temp_dir)
        
        # 查找解压后的内容
        extracted_items = os.listdir(temp_dir)
        
        # 创建目标目录
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)
        
        # 如果解压出来是一个文件夹，直接移动
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
            shutil.move(os.path.join(temp_dir, extracted_items[0]), target_path)
        else:
            # 否则创建目标文件夹并移动所有内容
            os.makedirs(target_path, exist_ok=True)
            for item in extracted_items:
                shutil.move(os.path.join(temp_dir, item), os.path.join(target_path, item))
        
        # 验证安装
        if os.path.exists(target_path):
            installed_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(target_path)
                for filename in filenames
            ) / (1024 * 1024)
            
            print()
            print("=" * 50)
            print("[结果] ✓ 安装成功")
            print(f"  安装路径: {target_path}")
            print(f"  占用空间: {installed_size:.2f} MB")
            print("=" * 50)
            print()
        else:
            raise RuntimeError("安装验证失败")
            
    except Exception as e:
        print()
        print("=" * 50)
        print("[结果] × 安装失败")
        print(f"  错误信息: {e}")
        print("=" * 50)
        sys.exit(1)
    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="安装 G2PWModel 模型")
    parser.add_argument("source_file", nargs="?", help="要安装的 zip 文件路径（可选，默认自动查找最新下载）")
    parser.add_argument("--force", "-f", action="store_true", help="强制安装（删除已存在的目标）")
    args = parser.parse_args()
    
    install(source_file=args.source_file, force=args.force)
