#!/bin/bash

# G2PWModel 安装脚本 (纯 Bash)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 查找项目根目录
find_project_root() {
    local dir="$SCRIPT_DIR"
    while [[ "$dir" != "/" ]]; do
        if [[ -f "$dir/.mon" ]] || [[ -f "$dir/pyproject.toml" ]] || [[ -d "$dir/.git" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    echo "$(cd "$SCRIPT_DIR/../../../.." && pwd)"
}

PROJECT_ROOT=$(find_project_root)

# 加载环境变量
ENV_FILE="${PROJECT_ROOT}/Env/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# 确定目标路径
if [[ -n "$G2PW_MODEL_PATH" ]]; then
    TARGET_PATH="${PROJECT_ROOT}/${G2PW_MODEL_PATH}"
else
    TARGET_PATH="${PROJECT_ROOT}/GPT_SoVITS/text/G2PWModel"
fi

# 获取源文件
if [[ $# -eq 0 ]]; then
    # 自动查找最近下载的文件
    SOURCE_FILE=$(find /tmp -name "G2PWModel_*.zip" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [[ -z "$SOURCE_FILE" ]]; then
        echo "错误: 未找到下载的模型文件"
        echo "用法: $0 <zip文件路径>"
        exit 1
    fi
    echo "自动找到文件: $SOURCE_FILE"
else
    SOURCE_FILE="$1"
fi

if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "错误: 文件不存在: $SOURCE_FILE"
    exit 1
fi

file_size=$(du -m "$SOURCE_FILE" 2>/dev/null | cut -f1)

echo "=================================================="
echo "[安装] G2PWModel 模型"
echo "=================================================="
echo "  源文件: $SOURCE_FILE"
echo "  文件大小: ${file_size} MB"
echo "  目标路径: $TARGET_PATH"
echo ""

# 检查目标路径
if [[ -d "$TARGET_PATH" ]]; then
    echo "  目标路径已存在，删除旧文件..."
    rm -rf "$TARGET_PATH"
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "解压文件到临时目录..."

if ! unzip -q "$SOURCE_FILE" -d "$TEMP_DIR"; then
    echo "错误: 解压失败"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 移动文件
mkdir -p "$(dirname "$TARGET_PATH")"

# 检查解压后的内容
items=($(ls -A "$TEMP_DIR"))
if [[ ${#items[@]} -eq 1 && -d "$TEMP_DIR/${items[0]}" ]]; then
    mv "$TEMP_DIR/${items[0]}" "$TARGET_PATH"
else
    mkdir -p "$TARGET_PATH"
    mv "$TEMP_DIR"/* "$TARGET_PATH/"
fi

rm -rf "$TEMP_DIR"

# 验证安装
if [[ -d "$TARGET_PATH" ]]; then
    installed_size=$(du -sm "$TARGET_PATH" 2>/dev/null | cut -f1)
    echo ""
    echo "=================================================="
    echo "[结果] ✓ 安装成功"
    echo "  安装路径: $TARGET_PATH"
    echo "  占用空间: ${installed_size} MB"
    echo "=================================================="
else
    echo "[结果] ✗ 安装失败"
    exit 1
fi
