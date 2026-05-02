#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${EMAIL:-download-acceptance-$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-password123}"
SAMPLE_URL="${SAMPLE_URL:-https://filesamples.com/samples/video/mp4/sample_640x360.mp4}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MAX_POLLS="${MAX_POLLS:-60}"

TOKEN="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Download Acceptance\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "{\"url\":\"${SAMPLE_URL}\",\"format_id\":\"best\",\"title\":\"Download Acceptance\",\"format_label\":\"best\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

STATE="queued"
for _ in $(seq 1 "${MAX_POLLS}"); do
  PAYLOAD="$(
    curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}" \
      -H "Authorization: Bearer ${TOKEN}"
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

curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}/download-link" \
  -H "Authorization: Bearer ${TOKEN}" >/dev/null

echo "Download task smoke passed: ${TASK_ID}"
