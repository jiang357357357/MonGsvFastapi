#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LAUNCHER="${PROJECT_ROOT}/Code/Main/launch.py"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_EXE="${PROJECT_ROOT}/.venv/bin/python"
else
  PYTHON_EXE="${PYTHON:-python3}"
fi

echo "========================================"
echo "  MonGSV - Production Launcher"
echo "========================================"
echo
echo "Project : ${PROJECT_ROOT}"
echo "Launcher: ${LAUNCHER}"
echo

if [[ ! -f "${LAUNCHER}" ]]; then
  echo "[ERROR] Launcher not found: ${LAUNCHER}" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"
exec "${PYTHON_EXE}" "${LAUNCHER}" "$@"
