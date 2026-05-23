#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-local}"
RUNTIME_DIR="${ROOT_DIR}/tmp/runtime"
WORKER_PID_FILE="${RUNTIME_DIR}/worker.pid"
WORKER_LOG_FILE="${RUNTIME_DIR}/worker.log"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/start.sh local             Start local API and Worker only (optional)
  ./scripts/start.sh docker            Start Docker API only
  ./scripts/start.sh docker:detached   Start Docker API and local Worker in background
  ./scripts/start.sh docker:stop       Stop Docker API and local Worker
  ./scripts/start.sh prod              Start production Docker stack with infra

Local mode only starts API and optional Worker; it does not start or install
PostgreSQL, Redis, or MinIO. The default Docker Compose file defines API +
Worker only. Production mode adds PostgreSQL, Redis, MinIO, Worker, and API
through the prod Compose override.
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

pid_is_running() {
  local pid="$1"
  [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null
}

start_worker_detached() {
  ensure_local_env
  mkdir -p "${RUNTIME_DIR}"

  if [ -f "${WORKER_PID_FILE}" ]; then
    local existing_pid
    existing_pid="$(cat "${WORKER_PID_FILE}" 2>/dev/null || true)"
    if pid_is_running "${existing_pid}"; then
      echo "Local Worker already running with PID ${existing_pid}"
      return
    fi
    rm -f "${WORKER_PID_FILE}"
  fi

  cd "${ROOT_DIR}"
  local py_bin
  py_bin="$(python_bin)"
  echo "Starting local Worker; log: ${WORKER_LOG_FILE}"
  PYTHON_BIN="${py_bin}" \
    PYTHONPATH="${PYTHONPATH:-}:apps/api:apps/worker:packages/shared" \
    RQ_WORKER_MODE="${RQ_WORKER_MODE:-simple}" \
    "${py_bin}" "${ROOT_DIR}/scripts/start_worker_daemon.py" "${ROOT_DIR}" "${WORKER_PID_FILE}" "${WORKER_LOG_FILE}" >/dev/null
}

stop_worker_detached() {
  if [ ! -f "${WORKER_PID_FILE}" ]; then
    return
  fi

  local pid
  pid="$(cat "${WORKER_PID_FILE}" 2>/dev/null || true)"
  rm -f "${WORKER_PID_FILE}"
  if ! pid_is_running "${pid}"; then
    return
  fi

  echo "Stopping local Worker with PID ${pid}"
  kill "${pid}" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    if ! pid_is_running "${pid}"; then
      return
    fi
    sleep 1
  done
  kill -TERM "${pid}" 2>/dev/null || true
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

start_docker() {
  ensure_local_env
  cd "${ROOT_DIR}"
  docker compose \
    --env-file .env \
    -f docker-compose.yml \
    up --build
}

start_docker_detached() {
  ensure_local_env
  cd "${ROOT_DIR}"
  docker compose \
    --env-file .env \
    -f docker-compose.yml \
    up -d --build
  start_worker_detached
}

stop_docker() {
  cd "${ROOT_DIR}"
  stop_worker_detached

  docker compose \
    --env-file .env \
    -f docker-compose.yml \
    down
}

start_prod() {
  cd "${ROOT_DIR}"
  if [ ! -f ".env.production" ]; then
    echo "Missing .env.production. Create it first:"
    echo "  cp .env.production.example .env.production"
    echo "Then replace every CHANGE_ME value before starting production."
    exit 1
  fi

  python3 scripts/validate_prod_env.py .env.production
  APP_ENV_FILE=.env.production docker compose \
    --env-file .env.production \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    up --build
}

case "${MODE}" in
  local)
    start_local
    ;;
  prod | production)
    start_prod
    ;;
  docker | compose)
    start_docker
    ;;
  docker:detached | compose:detached)
    start_docker_detached
    ;;
  docker:stop | compose:stop)
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
