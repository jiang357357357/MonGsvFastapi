#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECOSYSTEM="$SCRIPT_DIR/ecosystem.config.cjs"

if ! command -v pm2 &>/dev/null; then
  echo "[!] PM2 未安装，跳过停止"
  exit 0
fi

ACTION="${1:-stop}"
case "$ACTION" in
  stop)
    echo "[→] 正在停止 MonGSV ..."
    pm2 stop "$ECOSYSTEM"
    echo "[✓] 已停止"
    ;;
  delete)
    echo "[→] 正在删除 MonGSV 进程 ..."
    pm2 delete "$ECOSYSTEM"
    echo "[✓] 已删除"
    ;;
  *)
    echo "用法: $0 [stop|delete]"
    exit 1
    ;;
esac
