#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v pm2 &>/dev/null; then
  echo "[!] PM2 未安装"
  exit 1
fi

echo ""
echo "======================================================================"
echo "  MonGSV - PM2 进程状态"
echo "======================================================================"

case "${1:-}" in
  detail)
    pm2 show MonGSV
    ;;
  monit)
    pm2 monit
    ;;
  *)
    pm2 status
    ;;
esac
