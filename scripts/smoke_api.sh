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

RETRY_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/api/tasks/${TASK_ID}/retry")"
RETRY_TASK_ID="$(printf "%s" "${RETRY_RESPONSE}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
if [ "${RETRY_TASK_ID}" = "${TASK_ID}" ]; then
  echo "Expected retry to create a new task id" >&2
  exit 1
fi
printf "%s" "${RETRY_RESPONSE}" | "${PYTHON_BIN}" -c 'import json,sys; data=json.load(sys.stdin); assert data["retry_of_task_id"] and data["attempt_no"] >= 2'
OLD_RETRY_STATUS="$(
  curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${BASE_URL}/api/tasks/${TASK_ID}/retry"
)"
if [ "${OLD_RETRY_STATUS}" != "409" ]; then
  echo "Expected superseded retry to return 409, got ${OLD_RETRY_STATUS}" >&2
  exit 1
fi
curl -fsS -X POST "${BASE_URL}/api/tasks/${RETRY_TASK_ID}/cancel" >/dev/null || true

STREAM_OUTPUT="$(mktemp)"
curl -fsS --max-time 2 "${BASE_URL}/api/tasks/stream?limit=1" >"${STREAM_OUTPUT}" || true
if ! grep -q "event: tasks" "${STREAM_OUTPUT}"; then
  echo "Expected task stream to emit tasks event" >&2
  cat "${STREAM_OUTPUT}" >&2
  exit 1
fi
rm -f "${STREAM_OUTPUT}"

STATUS_CODE="$(
  curl -s -o /dev/null -w "%{http_code}" \
    "${BASE_URL}/api/tasks/${TASK_ID}/download-link"
)"

if [ "${STATUS_CODE}" != "409" ]; then
  echo "Expected unfinished task download-link to return 409, got ${STATUS_CODE}" >&2
  exit 1
fi

echo "API smoke passed"
