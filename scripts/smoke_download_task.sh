#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SAMPLE_URL="${SAMPLE_URL:-https://commons.wikimedia.org/wiki/File:%22Movbild-fizika%22_falo_en_Big_Buck_Bunny.webm}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MAX_POLLS="${MAX_POLLS:-60}"

cancel_active_tasks() {
  local task_ids
  task_ids="$(
    curl -fsS "${BASE_URL}/api/tasks" \
      | "${PYTHON_BIN}" -c 'import json,sys; print(" ".join(item["id"] for item in json.load(sys.stdin) if item.get("state") in {"queued","running"}))'
  )"
  for task_id in ${task_ids}; do
    curl -fsS -X POST "${BASE_URL}/api/tasks/${task_id}/cancel" >/dev/null || true
  done
}

cancel_active_tasks

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"${SAMPLE_URL}\",\"format_id\":\"best\",\"title\":\"Download Acceptance\",\"format_label\":\"best\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

STATE="queued"
for _ in $(seq 1 "${MAX_POLLS}"); do
  PAYLOAD="$(
    curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}"
  )"
  STATE="$(printf '%s' "${PAYLOAD}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["state"])')"
  if [ "${STATE}" = "succeeded" ]; then
    break
  fi
  if [ "${STATE}" = "failed" ] || [ "${STATE}" = "canceled" ]; then
    printf '%s\n' "${PAYLOAD}" >&2
    exit 1
  fi
  sleep 1
done

if [ "${STATE}" != "succeeded" ]; then
  echo "Expected task to succeed, got ${STATE}" >&2
  exit 1
fi

curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}/download-link" >/dev/null

echo "Download task smoke passed: ${TASK_ID}"
