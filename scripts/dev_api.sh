#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:apps/api:packages/shared"
export APP_ENV="${APP_ENV:-local}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -f ".env" ]; then
  echo "未找到 .env，已从 .env.example 创建本地开发配置"
  cp .env.example .env
fi

set -a
. ./.env
set +a

if [ "${API_RELOAD:-true}" = "true" ]; then
  "${PYTHON_BIN}" -m uvicorn app.main:app --host "${API_HOST:-127.0.0.1}" --port "${API_PORT:-8000}" --reload
else
  "${PYTHON_BIN}" -m uvicorn app.main:app --host "${API_HOST:-127.0.0.1}" --port "${API_PORT:-8000}"
fi
