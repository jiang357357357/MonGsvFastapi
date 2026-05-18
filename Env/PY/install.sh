#!/bin/bash

# Python 虚拟环境安装脚本
# 使用 UV 创建 Python 虚拟环境并安装依赖

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
echo -e "${CYAN}  Python 虚拟环境安装${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${GRAY}工作区: $WORKSPACE_ROOT${NC}"
echo ""

# 检查 UV 是否安装
if [ ! -f "$UV_EXE" ]; then
    echo -e "${RED}[✗] UV 未安装${NC}"
    echo -e "${YELLOW}    请先安装 UV 包管理器${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] UV 已安装${NC}"
echo ""

# 检查虚拟环境是否已存在
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[!] 虚拟环境已存在，将进行重新创建${NC}"
    echo -e "${GRAY}    位置: $VENV_DIR${NC}"
    echo ""
    echo -e "${CYAN}[→] 删除旧的虚拟环境...${NC}"
    rm -rf "$VENV_DIR"
    echo -e "${GREEN}    [✓] 旧环境已删除${NC}"
    echo ""
fi

# 1. 创建虚拟环境
echo -e "${CYAN}[→] 创建 Python 虚拟环境...${NC}"
echo -e "${GRAY}    使用 UV 创建虚拟环境...${NC}"

cd "$WORKSPACE_ROOT"

# 使用 UV 创建虚拟环境
if $UV_EXE venv .venv 2>&1 | while read -r line; do
    echo -e "${GRAY}    $line${NC}"
done; then
    :
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}    [✗] 安装失败: UV 创建虚拟环境失败${NC}"
    exit 1
fi

echo -e "${GREEN}    [✓] 虚拟环境创建成功${NC}"
echo ""

# 2. 验证 Python 可执行文件
echo -e "${CYAN}[→] 验证 Python 安装...${NC}"
if [ -f "$PYTHON_EXE" ]; then
    python_version=$($PYTHON_EXE --version 2>&1)
    echo -e "${GREEN}    [✓] Python 版本: $python_version${NC}"
else
    echo -e "${RED}    [✗] 安装失败: Python 可执行文件未找到: $PYTHON_EXE${NC}"
    exit 1
fi
echo ""

# 3. 安装依赖
PYPROJECT_FILE="$WORKSPACE_ROOT/pyproject.toml"
REQUIREMENTS_FILE="$WORKSPACE_ROOT/requirements.txt"

echo -e "${CYAN}[→] 检查依赖配置文件...${NC}"
if [ -f "$PYPROJECT_FILE" ]; then
    echo -e "${GRAY}    pyproject.toml: 存在${NC}"
else
    echo -e "${GRAY}    pyproject.toml: 不存在${NC}"
fi

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${GRAY}    requirements.txt: 存在${NC}"
else
    echo -e "${GRAY}    requirements.txt: 不存在${NC}"
fi
echo ""

if [ -f "$PYPROJECT_FILE" ]; then
    echo -e "${CYAN}[→] 安装项目依赖...${NC}"
    echo -e "${GRAY}    从 pyproject.toml 安装...${NC}"
    echo -e "${GRAY}    位置: $PYPROJECT_FILE${NC}"
    echo ""

    # 使用 uv sync 同步依赖（推荐方式）
    # 注意：不使用管道，以保留 uv 的进度条显示
    echo ""
    if $UV_EXE sync --link-mode=copy; then
        echo ""
        echo -e "${GREEN}    [✓] 依赖安装完成${NC}"
    else
        echo ""
        echo -e "${RED}    [✗] 依赖安装失败${NC}"
        exit 1
    fi
elif [ -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${CYAN}[→] 安装项目依赖...${NC}"
    echo -e "${GRAY}    从 requirements.txt 安装...${NC}"
    echo -e "${GRAY}    位置: $REQUIREMENTS_FILE${NC}"
    echo ""

    # 使用 uv pip install 安装依赖
    # 注意：不使用管道，以保留 uv 的进度条显示
    echo ""
    if $UV_EXE pip install -r "$REQUIREMENTS_FILE" --python "$PYTHON_EXE"; then
        echo ""
        echo -e "${GREEN}    [✓] 依赖安装完成${NC}"
    else
        echo ""
        echo -e "${RED}    [✗] 依赖安装失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[!] 未找到依赖配置文件，跳过依赖安装${NC}"
fi

echo ""
echo -e "${GREEN}[✓] Python 环境安装完成!${NC}"
echo ""
echo -e "${GRAY}虚拟环境位置: $VENV_DIR${NC}"
echo -e "${GRAY}Python 路径: $PYTHON_EXE${NC}"
echo ""

exit 0
