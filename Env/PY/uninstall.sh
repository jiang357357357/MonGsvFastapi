#!/bin/bash

# Python 虚拟环境卸载脚本
# 删除 UV 创建的 Python 虚拟环境

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

# 配置国内镜像源（加速下载）
export UV_INDEX_URL="https://pypi.mirrors.ustc.edu.cn/simple"
export UV_EXTRA_INDEX_URL="https://mirrors.nju.edu.cn/pytorch/whl/cu128"
export UV_CONCURRENT_DOWNLOADS=50
export UV_TIMEOUT=30

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Python 虚拟环境卸载${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${GRAY}工作区: $WORKSPACE_ROOT${NC}"
echo ""

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[!] 虚拟环境不存在${NC}"
    echo -e "${GRAY}    预期位置: $VENV_DIR${NC}"
    echo ""
    echo -e "${GREEN}[✓] 无需卸载${NC}"
    exit 0
fi

echo -e "${YELLOW}[!] 警告: 此操作将删除 Python 虚拟环境及所有已安装的包${NC}"
echo ""
echo -e "${CYAN}将要删除:${NC}"
echo -e "${GRAY}  - 虚拟环境目录: $VENV_DIR${NC}"
echo -e "${GRAY}  - 所有已安装的 Python 包${NC}"
echo ""
echo -e "${CYAN}[→] 开始卸载...${NC}"

# 1. 尝试结束占用虚拟环境的进程
echo ""
echo -e "${CYAN}[→] 检查并结束相关进程...${NC}"

# 查找使用虚拟环境的 Python 进程
python_pids=$(ps aux | grep "$VENV_DIR" | grep -v grep | awk '{print $2}' || true)

if [ -n "$python_pids" ]; then
    pid_count=$(echo "$python_pids" | wc -l)
    echo -e "${YELLOW}    找到 $pid_count 个相关进程${NC}"
    for pid in $python_pids; do
        proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        echo -e "${GRAY}    结束进程: $proc_name (PID: $pid)${NC}"
        if kill -TERM "$pid" 2>/dev/null; then
            echo -e "${GREEN}    [✓] 进程已结束${NC}"
        else
            echo -e "${YELLOW}    [!] 无法结束进程${NC}"
        fi
    done

    # 等待进程完全结束
    sleep 1
else
    echo -e "${GREEN}    [✓] 没有发现相关进程${NC}"
fi

# 2. 删除虚拟环境目录
echo ""
echo -e "${CYAN}[→] 删除虚拟环境目录...${NC}"
echo -e "${GRAY}    删除目录: $VENV_DIR${NC}"

if rm -rf "$VENV_DIR"; then
    echo -e "${GREEN}    [✓] 虚拟环境已删除${NC}"
else
    echo -e "${RED}    [✗] 删除失败${NC}"
    exit 1
fi

# 验证删除
echo ""
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}[✓] Python 环境卸载完成!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}[✗] 卸载验证失败 - 虚拟环境目录仍然存在${NC}"
    exit 1
fi
