#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${EMAIL:-demo@example.com}"
PASSWORD="${PASSWORD:-password123}"

curl -fsS "${BASE_URL}/health" >/dev/null
TOKEN="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Demo\"}" \
    | "${PYTHON_BIN:-python3}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
curl -fsS "${BASE_URL}/api/auth/me" -H "Authorization: Bearer ${TOKEN}" >/dev/null

echo "API smoke passed"
