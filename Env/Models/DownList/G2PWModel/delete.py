#!/usr/bin/env python3
import os
import sys
import shutil

# 添加 DownList 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import load_env_file, assume_yes

PROJECT_ROOT, ENV_DIR = load_env_file()

CONFIG = {
    "name": "中文字音转换模型",
    "path": "GPT_SoVITS/text/G2PWModel"
}

def delete():
    target_path = os.path.join(PROJECT_ROOT, CONFIG["path"])
    
    print("=" * 50)
    print(f"[删除] {CONFIG['name']}")
    print("=" * 50)
    print(f"  目标: {target_path}")
    
    if not os.path.exists(target_path):
        print("  [!] 文件不存在，无需删除")
        return
    
    if not assume_yes():
        confirm = input("\n  确认删除? (yes/no): ")
        if confirm.lower() != "yes":
            print("  [取消] 删除操作已取消")
            return
    
    shutil.rmtree(target_path)
    print("=" * 50)
    print("[结果] ✓ 删除完成")

if __name__ == "__main__":
    delete()
