#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_DIR}/outputs/logs"
mkdir -p "${LOG_DIR}"

timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

echo "[$(timestamp)] Starting daily NBA props run" >> "${LOG_DIR}/daily_runner.log"
cd "${REPO_DIR}"

# Prefer project venv if present; otherwise fallback to python3 on PATH.
if [[ -x "${REPO_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

{
  echo "[$(timestamp)] Command: ${PYTHON_BIN} -m app.main"
  "${PYTHON_BIN}" -m app.main
  echo "[$(timestamp)] Daily run completed"
} >> "${LOG_DIR}/daily_runner.log" 2>&1
