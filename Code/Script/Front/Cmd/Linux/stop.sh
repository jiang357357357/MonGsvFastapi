#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
while [[ "$REPO_ROOT" != "/" && ! -f "$REPO_ROOT/.monconfig" ]]; do
  REPO_ROOT="$(dirname "$REPO_ROOT")"
done

PORT="$(awk '
  /^\[frontend\]/{section=1; next}
  /^\[/{section=0}
  section && /^PORT=/{split($0,a,"="); print a[2]; exit}
' "$REPO_ROOT/.monconfig" | tr -d "[:space:]")"
PORT="${PORT:-40031}"

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti tcp:"$PORT" || true)"
  if [[ -n "$PIDS" ]]; then
    kill $PIDS
  else
    echo "Frontend port $PORT is free."
  fi
else
  echo "lsof not found; cannot stop by port $PORT" >&2
  exit 1
fi

