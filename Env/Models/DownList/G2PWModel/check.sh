#!/bin/bash

# G2PWModel 检查脚本 (纯 Bash)

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
    # 默认返回上级目录
    echo "$(cd "$SCRIPT_DIR/../../../.." && pwd)"
}

PROJECT_ROOT=$(find_project_root)
TARGET_PATH="${PROJECT_ROOT}/GPT_SoVITS/text/G2PWModel"

echo "=================================================="
echo "[检查] 中文字音转换模型"
echo "=================================================="
echo "  路径: $TARGET_PATH"
echo ""

FILES=("g2pW.onnx" "char_bopomofo_dict.json")
ALL_EXIST=true

for file in "${FILES[@]}"; do
    file_path="$TARGET_PATH/$file"
    if [[ -e "$file_path" ]]; then
        if [[ -d "$file_path" ]]; then
            size=$(du -sm "$file_path" 2>/dev/null | cut -f1)
        else
            size=$(du -sm "$file_path" 2>/dev/null | cut -f1)
        fi
        echo "  [✓] $file (${size} MB)"
    else
        echo "  [✗] $file - 缺失"
        ALL_EXIST=false
    fi
done

echo "=================================================="
if $ALL_EXIST; then
    echo "[结果] ✓ 所有文件检查通过"
    exit 0
else
    echo "[结果] ✗ 部分文件缺失"
    exit 1
fi
