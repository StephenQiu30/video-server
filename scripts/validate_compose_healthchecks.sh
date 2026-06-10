#!/usr/bin/env bash
set -euo pipefail

# Validate that the merged Docker Compose configuration includes healthchecks
# for the API service and all core infrastructure dependencies (postgres, redis, minio).
#
# Usage: ./scripts/validate_compose_healthchecks.sh [env-file]
# Requires: docker compose, python3

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE="${1:-.env.production.example}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

COMPOSE_JSON="$(docker compose \
  --env-file "${ENV_FILE}" \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  config --format json)"

python3 -c "
import json, sys

config = json.loads(sys.stdin.read())
services = config.get('services', {})

required = {'api', 'postgres', 'redis', 'minio'}
missing = []

for name in sorted(required):
    svc = services.get(name)
    if svc is None:
        missing.append(f'{name}: service not found in merged config')
        continue
    hc = svc.get('healthcheck')
    if hc is None:
        missing.append(f'{name}: healthcheck missing')
        continue
    test = hc.get('test')
    if not test:
        missing.append(f'{name}: healthcheck test is empty')
        continue
    print(f'  ✓ {name}: {test}')

if missing:
    print()
    print('FAILED: healthcheck validation errors:')
    for m in missing:
        print(f'  ✗ {m}')
    sys.exit(1)

print()
print('All core services have healthchecks configured.')
" <<< "${COMPOSE_JSON}"

echo "Compose healthcheck validation passed"
