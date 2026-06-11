#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/Code/GptSov_Front"

echo "========================================"
echo "  MonGSV - Build Frontend"
echo "========================================"
echo
echo "Project : ${PROJECT_ROOT}"
echo "Frontend: ${FRONTEND_DIR}"
echo

if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
  echo "[ERROR] Frontend package.json not found: ${FRONTEND_DIR}/package.json" >&2
  exit 1
fi

cd "${FRONTEND_DIR}"

if [[ ! -d node_modules ]]; then
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

npm run build
