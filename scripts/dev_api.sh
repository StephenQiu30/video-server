#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:apps/api:packages/shared"
export APP_ENV="${APP_ENV:-local}"

if [ ! -f ".env" ]; then
  echo "未找到 .env，已从 .env.example 创建本地开发配置"
  cp .env.example .env
fi

set -a
. ./.env
set +a

uvicorn app.main:app --host "${API_HOST:-127.0.0.1}" --port "${API_PORT:-8000}" --reload
