#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECOSYSTEM="$SCRIPT_DIR/ecosystem.config.cjs"

if ! command -v pm2 &>/dev/null; then
  echo "[!] PM2 未安装，请先执行: npm install -g pm2"
  exit 1
fi

echo ""
echo "======================================================================"
echo "  MonGSV - PM2 进程管理 (启动)"
echo "======================================================================"

cd "$SCRIPT_DIR/../../.."

# 先停止旧进程，避免端口冲突
"$SCRIPT_DIR/stop.sh" 2>/dev/null || true

echo "[→] 正在启动 MonGSV ..."
pm2 start "$ECOSYSTEM" "$@"
