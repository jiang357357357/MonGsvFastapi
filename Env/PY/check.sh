#!/bin/bash

# Python 虚拟环境检查脚本
# 检查 UV 创建的 Python 虚拟环境状态

set -e

# 颜色定义
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 获取脚本所在目录的父目录（工作区根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$(dirname "$(dirname "$SCRIPT_DIR")")" && pwd)"

# 定义路径
VENV_DIR="$WORKSPACE_ROOT/.venv"
PYTHON_EXE="$VENV_DIR/bin/python"
UV_EXE="$HOME/.local/bin/uv"

# 配置国内镜像源（加速下载）
export UV_INDEX_URL="https://pypi.mirrors.ustc.edu.cn/simple"
export UV_EXTRA_INDEX_URL="https://mirrors.nju.edu.cn/pytorch/whl/cu128"
export UV_CONCURRENT_DOWNLOADS=50
export UV_TIMEOUT=30

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Python 虚拟环境检查${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${GRAY}工作区: $WORKSPACE_ROOT${NC}"
echo ""

# 检查 UV 是否安装
if [ ! -f "$UV_EXE" ]; then
    echo -e "${RED}[✗] UV 未安装${NC}"
    echo -e "${YELLOW}    请先安装 UV 包管理器${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}[✓] UV 已安装${NC}"
if uv_version=$($UV_EXE --version 2>&1); then
    echo -e "${GRAY}    版本: $uv_version${NC}"
else
    echo -e "${YELLOW}    无法获取版本信息${NC}"
fi
echo ""
echo ""

# 检查虚拟环境是否存在
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}[✓] 虚拟环境已创建${NC}"
    echo -e "${GRAY}    位置: $VENV_DIR${NC}"
    echo ""

    # 检查 Python 可执行文件
    if [ -f "$PYTHON_EXE" ]; then
        echo -e "${GREEN}[✓] Python 可执行文件存在${NC}"

        # 获取 Python 版本
        if python_version=$($PYTHON_EXE --version 2>&1); then
            echo -e "${GRAY}    版本: $python_version${NC}"
        else
            echo -e "${YELLOW}    无法获取 Python 版本${NC}"
        fi

        echo ""
        echo ""

        # 检查已安装的包
        echo -e "${CYAN}[→] 检查已安装的包...${NC}"
        echo ""
        if $UV_EXE pip list --python "$PYTHON_EXE" 2>&1 | while read -r line; do
            echo -e "${GRAY}$line${NC}"
        done; then
            :
        else
            echo -e "${YELLOW}    无法列出已安装的包${NC}"
        fi

        echo ""
        echo ""
        echo -e "${GREEN}[✓] Python 环境检查完成 - 已配置${NC}"
        exit 0
    else
        echo -e "${RED}[✗] Python 可执行文件不存在${NC}"
        echo -e "${GRAY}    预期位置: $PYTHON_EXE${NC}"
        echo ""
        echo -e "${YELLOW}    虚拟环境可能已损坏，请重新安装${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${RED}[✗] 虚拟环境未创建${NC}"
    echo -e "${GRAY}    预期位置: $VENV_DIR${NC}"
    echo ""
    echo -e "${YELLOW}[!] 请运行安装脚本创建虚拟环境${NC}"
    echo ""
    exit 1
fi
