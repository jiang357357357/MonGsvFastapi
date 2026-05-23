#!/bin/bash
# ============================================================
# MonGSV 启动脚本 (PM2)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ECOSYSTEM="$SCRIPT_DIR/ecosystem.config.cjs"
LOG_DIR="$PROJECT_ROOT/Data/Logs/PM2"

PM2="$(command -v pm2 2>/dev/null || echo 'npx pm2')"

if ! $PM2 --version &>/dev/null; then
    echo "[错误] pm2 未安装，请执行: npm install -g pm2"
    exit 1
fi

mkdir -p "$LOG_DIR"

echo "============================================================"
echo "  MonGSV - 启动服务"
echo "============================================================"

cd "$PROJECT_ROOT"
$PM2 start "$ECOSYSTEM"

echo ""
$PM2 status
echo ""
echo "[完成] 服务已启动"
echo "  Backend API: http://localhost:40302/docs"
echo "  Frontend:    http://localhost:40031"
