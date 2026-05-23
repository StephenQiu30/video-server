#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-local}"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/start.sh local             Start local API only
  ./scripts/start.sh local:worker      Start local API + local Worker
  ./scripts/start.sh worker            Start local Worker only
  ./scripts/start.sh docker:up         Start deployment Docker stack in background
  ./scripts/start.sh docker            Start deployment Docker stack in foreground
  ./scripts/start.sh docker:down       Stop deployment Docker stack

Local mode is for development and does not start or install PostgreSQL, Redis,
or MinIO. Docker mode is for deployment and starts API, Worker, PostgreSQL,
Redis, and MinIO from .env.production.
USAGE
}

ensure_local_env() {
  if [ ! -f "${ROOT_DIR}/.env" ]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "Created .env from .env.example"
  fi
}

python_bin() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    echo "${PYTHON_BIN}"
    return
  fi
  if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
    echo "${ROOT_DIR}/.venv/bin/python"
    return
  fi
  echo "python3"
}

start_local() {
  ensure_local_env
  cd "${ROOT_DIR}"

  local py_bin
  py_bin="$(python_bin)"
  export PYTHON_BIN="${py_bin}"

  PIDS=()
  cleanup() {
    for pid in "${PIDS[@]:-}"; do
      kill "${pid}" 2>/dev/null || true
    done
    wait 2>/dev/null || true
  }
  trap cleanup INT TERM EXIT

  echo "Starting API: http://127.0.0.1:${API_PORT:-8000}"
  ./scripts/dev_api.sh &
  PIDS+=("$!")

  if [ "${START_WORKER:-false}" = "true" ]; then
    echo "Starting Worker"
    ./scripts/dev_worker.sh &
    PIDS+=("$!")
  else
    echo "Skipping Worker. Set START_WORKER=true if you need local queued downloads."
  fi

  echo "Local stack started. Press Ctrl+C to stop."
  while true; do
    for pid in "${PIDS[@]}"; do
      if ! kill -0 "${pid}" 2>/dev/null; then
        echo "One local process exited; stopping the rest."
        exit 1
      fi
    done
    sleep 2
  done
}

start_worker() {
  ensure_local_env
  cd "${ROOT_DIR}"
  local py_bin
  py_bin="$(python_bin)"
  export PYTHON_BIN="${py_bin}"
  echo "Starting Worker"
  exec ./scripts/dev_worker.sh
}

ensure_production_env() {
  cd "${ROOT_DIR}"
  if [ ! -f ".env.production" ]; then
    echo "Missing .env.production. Create it first:"
    echo "  cp .env.production.example .env.production"
    echo "Then replace every CHANGE_ME value before starting Docker deployment."
    exit 1
  fi
  python3 scripts/validate_prod_env.py .env.production
}

start_docker() {
  ensure_production_env
  cd "${ROOT_DIR}"
  APP_ENV_FILE=.env.production docker compose \
    --env-file .env.production \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    up --build
}

start_docker_detached() {
  ensure_production_env
  cd "${ROOT_DIR}"
  docker compose \
    --env-file .env.production \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    up -d --build
}

stop_docker() {
  cd "${ROOT_DIR}"
  docker compose \
    --env-file .env.production \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    down
}

case "${MODE}" in
  local)
    start_local
    ;;
  local:worker)
    START_WORKER=true start_local
    ;;
  worker)
    start_worker
    ;;
  docker | compose)
    start_docker
    ;;
  docker:up | compose:up | prod | production)
    start_docker_detached
    ;;
  docker:down | compose:down | docker:stop | compose:stop)
    stop_docker
    ;;
  -h | --help | help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
