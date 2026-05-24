#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
while [[ "$REPO_ROOT" != "/" && ! -f "$REPO_ROOT/.monconfig" ]]; do
  REPO_ROOT="$(dirname "$REPO_ROOT")"
done

if [[ ! -f "$REPO_ROOT/.monconfig" ]]; then
  echo "未找到 .monconfig" >&2
  exit 1
fi

FRONTEND_DIR="$REPO_ROOT/Code/GptSov_Front"
FRONTEND_PORT="$(awk '
  /^\[frontend\]/{section=1; next}
  /^\[/{section=0}
  section && /^PORT=/{split($0,a,"="); print a[2]; exit}
' "$REPO_ROOT/.monconfig" | tr -d "[:space:]")"
FRONTEND_PORT="${FRONTEND_PORT:-40031}"
cd "$FRONTEND_DIR"

if [[ ! -d node_modules ]]; then
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

if [[ "$MODE" == "prod" || "$MODE" == "production" || "$MODE" == "preview" ]]; then
  npm run build
  exec npx vite preview --host 0.0.0.0 --port "$FRONTEND_PORT"
fi

exec npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
