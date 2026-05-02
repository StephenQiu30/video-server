#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-local}"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/start.sh local   Start local API and Web only
  ./scripts/start.sh docker  Start default Docker API and Web only
  ./scripts/start.sh prod    Start production Docker stack with infra

Local mode only starts project processes and does not start or install
PostgreSQL, Redis, or MinIO. The default Docker Compose file also only defines
Web and API, and reads .env plus DOCKER_* URLs to reach existing host services.
Set START_WORKER=true when you need the local RQ Worker and already have Redis
available. Production mode adds PostgreSQL, Redis, MinIO, Worker, API, and Web
through the prod Compose override.
USAGE
}

ensure_local_env() {
  if [ ! -f "${ROOT_DIR}/.env" ]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "Created .env from .env.example"
  fi
}

start_local() {
  ensure_local_env
  cd "${ROOT_DIR}"

  if [ ! -d "apps/web/node_modules" ]; then
    echo "apps/web/node_modules not found. Run: cd apps/web && npm install"
    exit 1
  fi

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

  echo "Starting Web: http://127.0.0.1:3000"
  (
    cd "${ROOT_DIR}/apps/web"
    UMI_APP_API_BASE_URL="${UMI_APP_API_BASE_URL:-http://127.0.0.1:8000}" npm run dev
  ) &
  PIDS+=("$!")

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
    -f infra/docker/docker-compose.yml \
    up --build
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
  APP_ENV_FILE=../../.env.production docker compose \
    --env-file .env.production \
    -f infra/docker/docker-compose.yml \
    -f infra/docker/docker-compose.prod.yml \
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
  -h | --help | help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
