#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SAMPLE_URL="${SAMPLE_URL:-https://example.com/sample.mp4}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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

curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/ready" >/dev/null
cancel_active_tasks

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"${SAMPLE_URL}\",\"format_id\":\"best\",\"title\":\"[Smoke] API Sample\",\"format_label\":\"best\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

curl -fsS "${BASE_URL}/api/tasks" >/dev/null
curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}" >/dev/null
curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}/events" >/dev/null
curl -fsS -X POST "${BASE_URL}/api/tasks/${TASK_ID}/cancel" >/dev/null

RETRY_TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks/${TASK_ID}/retry" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"
if [ "${RETRY_TASK_ID}" = "${TASK_ID}" ]; then
  echo "Expected retry to create a new task id" >&2
  exit 1
fi
curl -fsS -X POST "${BASE_URL}/api/tasks/${RETRY_TASK_ID}/cancel" >/dev/null || true

STATUS_CODE="$(
  curl -s -o /dev/null -w "%{http_code}" \
    "${BASE_URL}/api/tasks/${TASK_ID}/download-link"
)"

if [ "${STATUS_CODE}" != "409" ]; then
  echo "Expected unfinished task download-link to return 409, got ${STATUS_CODE}" >&2
  exit 1
fi

echo "API smoke passed"
