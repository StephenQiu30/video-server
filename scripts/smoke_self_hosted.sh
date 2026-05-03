#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export BASE_URL
export PYTHON_BIN

cd "${ROOT_DIR}"

curl -fsS "${BASE_URL}/health" >/dev/null
READY_PAYLOAD="$(curl -fsS "${BASE_URL}/ready")"
export READY_PAYLOAD
"${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["READY_PAYLOAD"])
required = {"database", "redis", "queue", "storage", "media_tools", "download_work_dir"}
missing = required - set(payload.get("checks") or {})
if missing:
    raise SystemExit(f"missing readiness checks: {', '.join(sorted(missing))}")
if payload.get("status") != "ok":
    raise SystemExit(json.dumps(payload, ensure_ascii=False))
print("Readiness checks passed")
PY

"${ROOT_DIR}/scripts/smoke_parse_samples.sh"
"${ROOT_DIR}/scripts/smoke_api.sh"
"${ROOT_DIR}/scripts/smoke_download_task.sh"
"${ROOT_DIR}/scripts/cleanup_expired_outputs.sh"

echo "Self-hosted smoke passed"
