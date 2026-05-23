#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
API_TOKEN="${API_TOKEN:-}"
SMOKE_SAMPLE_FILE="${SMOKE_SAMPLE_FILE:-docs/05-测试验收/smoke-platform-samples.example.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -z "${API_TOKEN}" ]; then
  echo "API_TOKEN is required. Create or reuse a login token before running platform smoke tests." >&2
  exit 2
fi

if [ ! -f "${SMOKE_SAMPLE_FILE}" ]; then
  echo "SMOKE_SAMPLE_FILE not found: ${SMOKE_SAMPLE_FILE}" >&2
  exit 2
fi

"${PYTHON_BIN}" - "${API_BASE_URL}" "${API_TOKEN}" "${SMOKE_SAMPLE_FILE}" <<'PY'
import json
import sys
from urllib import error, request

base_url, token, sample_file = sys.argv[1:4]
with open(sample_file, "r", encoding="utf-8") as handle:
    samples = json.load(handle)

if not isinstance(samples, list) or not samples:
    raise SystemExit("sample file must contain a non-empty JSON array")

for sample in samples:
    name = sample.get("name") or sample.get("url")
    url = sample["url"]
    expected_platform_id = sample.get("expected_platform_id")
    payload = json.dumps({"url": url}).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}/api/parse",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body
        print(f"parse failed: {name} | status={exc.code} | detail={detail}")
        raise SystemExit(1) from exc

    platform_id = data.get("platform_id")
    formats = data.get("formats") or []
    if expected_platform_id and platform_id != expected_platform_id:
        raise SystemExit(f"{name}: expected platform_id={expected_platform_id}, got {platform_id}")
    if not formats:
        raise SystemExit(f"{name}: parse succeeded but returned no formats")
    print(f"parse ok: {name} | platform_id={platform_id} | formats={len(formats)}")

print("Platform parse smoke passed")
PY
