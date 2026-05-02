#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${EMAIL:-demo-$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-password123}"
SAMPLE_URL="${SAMPLE_URL:-https://example.com/sample.mp4}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/ready" >/dev/null
TOKEN="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Demo\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
curl -fsS "${BASE_URL}/api/auth/me" -H "Authorization: Bearer ${TOKEN}" >/dev/null

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "{\"url\":\"${SAMPLE_URL}\",\"format_id\":\"best\",\"title\":\"Smoke Sample\",\"format_label\":\"best\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

curl -fsS "${BASE_URL}/api/tasks" -H "Authorization: Bearer ${TOKEN}" >/dev/null
curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}" -H "Authorization: Bearer ${TOKEN}" >/dev/null
curl -fsS -X POST "${BASE_URL}/api/tasks/${TASK_ID}/cancel" -H "Authorization: Bearer ${TOKEN}" >/dev/null

STATUS_CODE="$(
  curl -s -o /dev/null -w "%{http_code}" \
    "${BASE_URL}/api/tasks/${TASK_ID}/download-link" \
    -H "Authorization: Bearer ${TOKEN}"
)"

if [ "${STATUS_CODE}" != "409" ]; then
  echo "Expected unfinished task download-link to return 409, got ${STATUS_CODE}" >&2
  exit 1
fi

echo "API smoke passed"
