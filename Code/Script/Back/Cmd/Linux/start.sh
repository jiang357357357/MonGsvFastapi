#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
while [[ "$REPO_ROOT" != "/" && ! -f "$REPO_ROOT/.monconfig" ]]; do
  REPO_ROOT="$(dirname "$REPO_ROOT")"
done

if [[ ! -f "$REPO_ROOT/.monconfig" ]]; then
  echo "未找到 .monconfig" >&2
  exit 1
fi

PYTHON_EXE="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_EXE" ]]; then
  PYTHON_EXE="python"
fi

cd "$REPO_ROOT"
exec "$PYTHON_EXE" "$REPO_ROOT/Code/FastApi/Base/Gateway/run_unified_gateway.py" "$@"
