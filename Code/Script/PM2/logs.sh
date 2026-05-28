#!/usr/bin/env bash
set -euo pipefail

if ! command -v pm2 &>/dev/null; then
  echo "[!] PM2 未安装"
  exit 1
fi

LINES="${2:-50}"
NAME="${1:-MonGSV}"

pm2 logs "$NAME" --lines "$LINES"
