#!/usr/bin/env bash
# ============================================================
# MonGSV 停止脚本 (PM2)
# ============================================================
set -euo pipefail

if command -v pm2 >/dev/null 2>&1; then
  PM2=(pm2)
elif command -v npx >/dev/null 2>&1; then
  PM2=(npx pm2)
else
  echo "[错误] 未找到 pm2 或 npx" >&2
  exit 1
fi

if ! "${PM2[@]}" --version >/dev/null 2>&1; then
  echo "[错误] pm2 不可用，请执行: npm install -g pm2" >&2
  exit 1
fi

echo "============================================================"
echo "  MonGSV - 停止 PM2 服务"
echo "============================================================"

"${PM2[@]}" stop MonGsvBackend MonGsvFrontend

echo ""
"${PM2[@]}" status
echo ""
echo "[完成] 服务已停止"

