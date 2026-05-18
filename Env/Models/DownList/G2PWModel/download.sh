#!/bin/bash

# G2PWModel 下载脚本 (纯 Bash)

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

# 配置
REPO="XXXXRT/GPT-SoVITS-Pretrained"
FILE="G2PWModel.zip"
OUTPUT_DIR="${TMPDIR:-/tmp}"
OUTPUT_FILE="${OUTPUT_DIR}/G2PWModel_$(date +%s).zip"

# 安装目标路径
INSTALL_TARGET="${PROJECT_ROOT}/GPT_SoVITS/text/G2PWModel"

# 获取 HF 端点
get_hf_endpoint() {
    if [[ -n "$HF_ENDPOINT" ]]; then
        echo "$HF_ENDPOINT"
    else
        echo "https://hf-mirror.com"
    fi
}

HF_ENDPOINT=$(get_hf_endpoint)
URL="${HF_ENDPOINT}/${REPO}/resolve/main/${FILE}"

echo "=================================================="
echo "[下载] 中文字音转换模型"
echo "=================================================="
echo "  仓库: $REPO"
echo "  文件: $FILE"
echo "  端点: $HF_ENDPOINT"
echo ""
echo "  下载位置: $OUTPUT_FILE"
echo "  安装目标: $INSTALL_TARGET"
echo ""

# 下载函数
download_with_progress() {
    local url="$1"
    local output="$2"

    if command -v wget &> /dev/null; then
        # 使用 wget，显示百分比进度
        echo "  [→] 使用 wget 下载..."
        wget --show-progress --progress=bar:force -O "$output" "$url" 2>&1
        return ${PIPESTATUS[0]}
    elif command -v curl &> /dev/null; then
        # 使用 curl，显示简洁进度
        echo "  [→] 使用 curl 下载..."
        curl -L --progress-bar -o "$output" "$url"
        return $?
    else
        echo "错误: 未找到 wget 或 curl"
        return 1
    fi
}

# 开始下载
echo "  [↓] 开始下载..."
echo ""

if download_with_progress "$URL" "$OUTPUT_FILE"; then
    file_size=$(du -m "$OUTPUT_FILE" 2>/dev/null | cut -f1)
    echo ""
    echo "=================================================="
    echo "[结果] ✓ 下载完成"
    echo "  文件大小: ${file_size} MB"
    echo "  保存位置: $OUTPUT_FILE"
    echo "  安装目标: $INSTALL_TARGET"
    echo "=================================================="
    echo ""
    # 输出下载文件路径供 App 捕获
    echo "[DOWNLOADED_FILE] $OUTPUT_FILE"
    echo ""
else
    echo ""
    echo "=================================================="
    echo "[结果] ✗ 下载失败"
    echo "=================================================="
    rm -f "$OUTPUT_FILE"
    exit 1
fi
