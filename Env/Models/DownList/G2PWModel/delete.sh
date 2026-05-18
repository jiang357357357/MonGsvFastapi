#!/bin/bash

# G2PWModel 删除脚本 (纯 Bash)

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

echo "=================================================="
echo "[删除] G2PWModel 模型"
echo "=================================================="
echo "  目标路径: $TARGET_PATH"
echo ""

if [[ ! -d "$TARGET_PATH" ]]; then
    echo "模型目录不存在，无需删除"
    exit 0
fi

# 计算大小
size=$(du -sm "$TARGET_PATH" 2>/dev/null | cut -f1)

read -p "确认删除 ${size} MB 的模型文件? (y/N): " response
if [[ "$response" =~ ^[Yy]$ ]]; then
    rm -rf "$TARGET_PATH"
    echo ""
    echo "=================================================="
    echo "[结果] ✓ 删除成功"
    echo "  释放空间: ${size} MB"
    echo "=================================================="
else
    echo "删除已取消"
fi
