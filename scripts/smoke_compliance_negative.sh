#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL_A="${EMAIL_A:-negative-a-$(date +%s)@example.com}"
EMAIL_B="${EMAIL_B:-negative-b-$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-password123}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

status_code() {
  curl -s -o /tmp/stephen-video-smoke-response.json -w "%{http_code}" "$@"
}

expect_code() {
  local expected="$1"
  shift
  local actual
  actual="$(status_code "$@")"
  if [ "${actual}" != "${expected}" ]; then
    echo "Expected HTTP ${expected}, got ${actual}" >&2
    cat /tmp/stephen-video-smoke-response.json >&2 || true
    exit 1
  fi
}

assert_no_forbidden_runtime_code() {
  "${PYTHON_BIN}" - <<'PY'
from pathlib import Path

roots = [Path("apps/api/app"), Path("apps/worker/worker"), Path("packages/shared")]
forbidden = [
    "cookiefile",
    "cookiesfrombrowser",
    "cookies_from_browser",
    "bilibili",
    "douyin",
    "drm_bypass",
    "paywall_bypass",
]
hits: list[str] = []
for root in roots:
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            if needle in text:
                hits.append(f"{path}:{needle}")
if hits:
    print("Forbidden runtime bypass markers found:")
    print("\n".join(hits))
    raise SystemExit(1)
print("runtime bypass static scan passed")
PY
}

curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/ready" >/dev/null

expect_code 401 -X POST "${BASE_URL}/api/parse" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://vimeo.com/777912896"}'

REGISTER_A="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL_A}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Negative A\"}"
)"
TOKEN_A="$(printf '%s' "${REGISTER_A}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

expect_code 409 -X POST "${BASE_URL}/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL_A}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Duplicate\"}"

expect_code 401 -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL_A}\",\"password\":\"wrong-password\"}"

REGISTER_B="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL_B}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Negative B\"}"
)"
TOKEN_B="$(printf '%s' "${REGISTER_B}" | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -d '{"url":"https://example.com/sample.mp4?token=secret&signature=secret","format_id":"best","title":"Negative Ownership","format_label":"best"}' \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

expect_code 404 "${BASE_URL}/api/tasks/${TASK_ID}" \
  -H "Authorization: Bearer ${TOKEN_B}"

expect_code 409 "${BASE_URL}/api/tasks/${TASK_ID}/download-link" \
  -H "Authorization: Bearer ${TOKEN_A}"

assert_no_forbidden_runtime_code

echo "Compliance negative smoke passed"
