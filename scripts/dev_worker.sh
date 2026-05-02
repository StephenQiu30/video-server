#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:apps/api:apps/worker:packages/shared"
export APP_ENV="${APP_ENV:-local}"
export RQ_WORKER_MODE="${RQ_WORKER_MODE:-simple}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -f ".env" ]; then
  echo "未找到 .env，已从 .env.example 创建本地开发配置"
  cp .env.example .env
fi

set -a
. ./.env
set +a

"${PYTHON_BIN}" -m worker.main
