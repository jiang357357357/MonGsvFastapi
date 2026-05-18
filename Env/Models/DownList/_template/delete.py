#!/usr/bin/env python3
"""
通用模块删除脚本模板

使用方法：
1. 复制此文件到新模块目录
2. 修改 CONFIG 字典中的配置
3. 如需自定义删除逻辑，重写 delete() 函数
"""
import os
import sys
import shutil

# 添加 _template 目录到路径以导入 common
_template_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_template"
)
sys.path.insert(0, _template_dir)
from common import load_env_file, assume_yes

PROJECT_ROOT, ENV_DIR = load_env_file()

# ============================================================
# 配置区域 - 根据实际模块修改
# ============================================================
CONFIG = {
    "name": "模块名称",
    "env_var": "ENV_VAR_NAME",  # 环境变量名称
    "default_path": "default/path",  # 默认相对路径
}


def get_target_path():
    """从环境变量获取目标路径"""
    rel_path = os.environ.get(CONFIG["env_var"], CONFIG["default_path"])
    return os.path.join(PROJECT_ROOT, rel_path)


def delete():
    """删除模块文件"""
    target_path = get_target_path()

    print("=" * 50)
    print(f"[删除] {CONFIG['name']}")
    print("=" * 50)
    print(f"  目标: {target_path}")

    if not os.path.exists(target_path):
        print("  [!] 文件不存在，无需删除")
        print("=" * 50)
        return

    if not assume_yes():
        confirm = input("\n  确认删除? (yes/no): ")
        if confirm.lower() != "yes":
            print("  [取消] 删除操作已取消")
            print("=" * 50)
            return

    try:
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
        print("=" * 50)
        print("[结果] ✓ 删除完成")
    except Exception as e:
        print(f"  [!] 删除失败: {e}")
        print("=" * 50)
        print("[结果] ✗ 删除失败")
        sys.exit(1)


if __name__ == "__main__":
    delete()
