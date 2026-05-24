#!/usr/bin/env bash
# ============================================================
# MonGSV 启动脚本 (PM2)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ECOSYSTEM="$SCRIPT_DIR/ecosystem.config.cjs"
LOG_DIR="$PROJECT_ROOT/Data/Logs/PM2"

if command -v pm2 >/dev/null 2>&1; then
  PM2=(pm2)
elif command -v npx >/dev/null 2>&1; then
  PM2=(npx pm2)
else
  echo "[错误] 未找到 pm2 或 npx，请先安装 Node.js/PM2" >&2
  exit 1
fi

if ! "${PM2[@]}" --version >/dev/null 2>&1; then
  echo "[错误] pm2 不可用，请执行: npm install -g pm2" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

echo "============================================================"
echo "  MonGSV - 启动 PM2 服务"
echo "============================================================"

cd "$PROJECT_ROOT"
"${PM2[@]}" start "$ECOSYSTEM"

echo ""
"${PM2[@]}" status
echo ""
echo "[完成] 服务已启动"
echo "  Backend API: http://localhost:40302/docs"
echo "  Frontend:    http://localhost:40031"

