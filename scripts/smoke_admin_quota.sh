#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin-$(date +%s)@example.com}"
USER_EMAIL="${USER_EMAIL:-quota-$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-password123}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

status_code() {
  curl -s -o /tmp/stephen-video-admin-smoke-response.json -w "%{http_code}" "$@"
}

expect_code() {
  local expected="$1"
  shift
  local actual
  actual="$(status_code "$@")"
  if [ "${actual}" != "${expected}" ]; then
    echo "Expected HTTP ${expected}, got ${actual}" >&2
    cat /tmp/stephen-video-admin-smoke-response.json >&2 || true
    exit 1
  fi
}

ADMIN_PAYLOAD="{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Admin\"}"
ADMIN_STATUS="$(
  curl -s -o /tmp/stephen-video-admin-register.json -w "%{http_code}" -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "${ADMIN_PAYLOAD}"
)"
if [ "${ADMIN_STATUS}" = "201" ]; then
  ADMIN_REGISTER="$(cat /tmp/stephen-video-admin-register.json)"
elif [ "${ADMIN_STATUS}" = "409" ]; then
  ADMIN_REGISTER="$(
    curl -fsS -X POST "${BASE_URL}/api/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${PASSWORD}\"}"
  )"
else
  echo "Expected admin register to return 201 or 409, got ${ADMIN_STATUS}" >&2
  cat /tmp/stephen-video-admin-register.json >&2 || true
  exit 1
fi
ADMIN_TOKEN="$(printf '%s' "${ADMIN_REGISTER}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
ADMIN_IS_ADMIN="$(printf '%s' "${ADMIN_REGISTER}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["user"]["is_admin"])')"
if [ "${ADMIN_IS_ADMIN}" != "True" ]; then
  echo "Expected ${ADMIN_EMAIL} to be admin. Start API with ADMIN_EMAILS=${ADMIN_EMAIL}" >&2
  exit 1
fi

USER_REGISTER="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${USER_EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Quota User\"}"
)"
USER_TOKEN="$(printf '%s' "${USER_REGISTER}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
USER_ID="$(printf '%s' "${USER_REGISTER}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["user"]["id"])')"

curl -fsS "${BASE_URL}/api/admin/users" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" >/dev/null

curl -fsS -X PATCH "${BASE_URL}/api/admin/users/${USER_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"daily_task_quota":0}' >/dev/null

expect_code 403 "${BASE_URL}/api/admin/users" \
  -H "Authorization: Bearer ${USER_TOKEN}"

expect_code 429 -X POST "${BASE_URL}/api/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -d '{"url":"https://example.com/sample.mp4","format_id":"best","title":"Quota Blocked","format_label":"best"}'

echo "Admin and quota smoke passed"
