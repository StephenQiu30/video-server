#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="${PYTHONPATH:-apps/api:apps/worker:packages/shared}"

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

assert_no_forbidden_runtime_code() {
  "${PYTHON_BIN}" - <<'PY'
from pathlib import Path

runtime_roots = [Path("apps/api/app"), Path("apps/worker/worker"), Path("packages/shared")]
forbidden = [
    "cookiefile",
    "drm_bypass",
    "paywall_bypass",
    "member_bypass",
    "private_bypass",
]
hits: list[str] = []
for root in runtime_roots:
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

assert_cookie_boundary() {
  "${PYTHON_BIN}" - <<'PY'
from pathlib import Path

allowed_cookie_reader_files = {
    Path("apps/worker/worker/jobs.py"),
}
allowed_cookie_config_files = {
    Path("apps/api/app/core/config.py"),
    Path("apps/worker/worker/jobs.py"),
}
cookie_reader_hits: list[str] = []
cookie_config_hits: list[str] = []

for root in [Path("apps/api/app"), Path("apps/worker/worker")]:
    for path in root.rglob("*"):
        if path.suffix not in {".py", ".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "cookiesfrombrowser" in text and path not in allowed_cookie_reader_files:
            cookie_reader_hits.append(str(path))
        if "ytdlp_cookies_from_browser" in text and path not in allowed_cookie_config_files:
            cookie_config_hits.append(str(path))

if cookie_reader_hits or cookie_config_hits:
    print("Cookie boundary violation found:")
    print("\n".join(cookie_reader_hits + cookie_config_hits))
    raise SystemExit(1)
print("local Worker browser-cookie exception check passed")
PY
}

assert_url_redaction() {
  "${PYTHON_BIN}" - <<'PY'
from app.utils.sanitize import redact_url

url = redact_url("https://example.com/video?id=1&token=secret&signature=abc&cookie=value")
for secret in ("secret", "abc", "value"):
    if secret in url:
        raise SystemExit(f"sensitive value leaked: {secret}")
print("url redaction check passed")
PY
}

curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/ready" >/dev/null
cancel_active_tasks

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://example.com/sample.mp4","format_id":"best","title":"[Smoke] Negative State","format_label":"best"}' \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

expect_code 409 "${BASE_URL}/api/tasks/${TASK_ID}/download-link"

assert_url_redaction
assert_no_forbidden_runtime_code
assert_cookie_boundary

echo "Compliance negative smoke passed"
