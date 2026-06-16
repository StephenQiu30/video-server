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

port_listener() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :${port}" 2>/dev/null || true
    return
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -an 2>/dev/null | grep "[.:]${port} .*LISTEN" || true
  fi
}

ensure_port_available() {
  local host="$1"
  local port="$2"
  local listeners
  listeners="$(port_listener "${port}")"
  if [ -z "${listeners}" ]; then
    return
  fi

  echo "Port ${host}:${port} is already in use." >&2
  echo "${listeners}" >&2
  echo "" >&2
  echo "Stop the existing process first, or start this API on another port:" >&2
  echo "  API_PORT=8001 npm start" >&2
  exit 1
}

preflight_check() {
  echo "检查本机依赖服务..."
  if ! "${ROOT_DIR}/scripts/check_local_services.sh"; then
    echo "" >&2
    echo "依赖服务未就绪，请先启动缺失的服务，或设置 SKIP_PREFLIGHT_CHECK=1 跳过检查。" >&2
    return 1
  fi
  echo ""
}

start_local() {
  ensure_local_env
  cd "${ROOT_DIR}"

  local py_bin
  py_bin="$(python_bin)"
  export PYTHON_BIN="${py_bin}"

  # 启动前依赖预检（可跳过）
  if [ "${SKIP_PREFLIGHT_CHECK:-0}" != "1" ]; then
    preflight_check
  else
    echo "SKIP_PREFLIGHT_CHECK=1，跳过依赖预检。"
  fi

  local api_host="${API_HOST:-127.0.0.1}"
  local api_port="${API_PORT:-8000}"
  ensure_port_available "${api_host}" "${api_port}"

  PIDS=()
  cleanup() {
    for pid in "${PIDS[@]:-}"; do
      kill "${pid}" 2>/dev/null || true
    done
    wait 2>/dev/null || true
  }
  trap cleanup INT TERM EXIT

  echo "Starting API: http://${api_host}:${api_port}"
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

  # 启动前依赖预检（可跳过）
  if [ "${SKIP_PREFLIGHT_CHECK:-0}" != "1" ]; then
    preflight_check
  else
    echo "SKIP_PREFLIGHT_CHECK=1，跳过依赖预检。"
  fi

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
