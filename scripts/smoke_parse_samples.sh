#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${EMAIL:-parse-acceptance-$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-password123}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

SAMPLES=(
  "https://vimeo.com/777912896|Twenty Years of Creative Commons (in Sixty Seconds)|CC BY 4.0"
  "https://vimeo.com/13864570|A Shared Culture|Creative Commons channel"
  "https://vimeo.com/12548408|Public Domain Video for SAW Video by RS and VC|Public Domain channel"
)

TOKEN="$(
  curl -fsS -X POST "${BASE_URL}/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"Parse Acceptance\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

for sample in "${SAMPLES[@]}"; do
  IFS="|" read -r url title license <<< "${sample}"
  PAYLOAD="$("${PYTHON_BIN}" -c 'import json,sys; print(json.dumps({"url": sys.argv[1]}))' "${url}")"
  RESPONSE="$(
    curl -fsS -X POST "${BASE_URL}/api/parse" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${TOKEN}" \
      -d "${PAYLOAD}"
  )"
  printf '%s' "${RESPONSE}" | "${PYTHON_BIN}" -c '
import json, sys

payload = json.load(sys.stdin)
if not payload.get("title"):
    raise SystemExit("missing title")
if not payload.get("formats"):
    raise SystemExit("missing formats")
title = payload.get("title")
formats = payload.get("formats")
print(f"parse ok: {title} | formats={len(formats)}")
'
  echo "sample source: ${title} (${license})"
done

echo "Parse samples smoke passed"
