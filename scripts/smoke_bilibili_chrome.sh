#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BILIBILI_SAMPLE_URL="${BILIBILI_SAMPLE_URL:-https://www.bilibili.com/video/BV1iCR7BEEvo/?spm_id_from=333.1007.tianma.1-1-1.click}"
MAX_POLLS="${MAX_POLLS:-180}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"
TMP_DIR="${TMPDIR:-/tmp}"
PARSE_RESPONSE="${TMP_DIR}/stephen-video-bilibili-parse.json"
TASK_RESPONSE="${TMP_DIR}/stephen-video-bilibili-task.json"
TASK_POLL_RESPONSE="${TMP_DIR}/stephen-video-bilibili-task-poll.json"
DOWNLOAD_RESPONSE="${TMP_DIR}/stephen-video-bilibili-download.json"
DOWNLOAD_OUTPUT="${TMP_DIR}/stephen-video-bilibili-download.bin"
TASK_PAYLOAD="${TMP_DIR}/stephen-video-bilibili-task-payload.json"

export PYTHONPATH="${PYTHONPATH:-apps/api:apps/worker:packages/shared}"

curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/ready" >/dev/null

curl -fsS -X POST "${BASE_URL}/api/parse" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${BILIBILI_SAMPLE_URL}\"}" \
  >"${PARSE_RESPONSE}"

"${PYTHON_BIN}" - "${PARSE_RESPONSE}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload.get("title"), "parse title missing"
assert isinstance(payload.get("duration_seconds"), int), "duration_seconds should be int"
formats = payload.get("formats") or []
assert formats and formats[0].get("format_id") == "bestvideo+bestaudio/best", "recommended format missing"
print(f"Parsed: {payload['title']}")
PY

"${PYTHON_BIN}" - "${PARSE_RESPONSE}" "${BILIBILI_SAMPLE_URL}" >"${TASK_PAYLOAD}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
source_url = sys.argv[2]
recommended = payload["formats"][0]
print(json.dumps({
    "url": source_url,
    "title": payload.get("title"),
    "cover_url": payload.get("cover_url"),
    "duration_seconds": payload.get("duration_seconds"),
    "format_id": recommended["format_id"],
    "format_label": recommended["label"],
}, ensure_ascii=False))
PY

curl -fsS -X POST "${BASE_URL}/api/tasks" \
  -H "Content-Type: application/json" \
  -d @"${TASK_PAYLOAD}" \
  >"${TASK_RESPONSE}"

TASK_ID="$("${PYTHON_BIN}" - "${TASK_RESPONSE}" <<'PY'
import json
import sys

print(json.load(open(sys.argv[1], encoding="utf-8"))["id"])
PY
)"

echo "Created task: ${TASK_ID}"

for ((i = 1; i <= MAX_POLLS; i++)); do
  curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}" >"${TASK_POLL_RESPONSE}"
  STATE="$("${PYTHON_BIN}" - "${TASK_POLL_RESPONSE}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
print(payload.get("state", ""))
PY
)"
  PROGRESS="$("${PYTHON_BIN}" - "${TASK_POLL_RESPONSE}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
print(payload.get("progress", 0))
PY
)"
  echo "Task state: ${STATE} (${PROGRESS}%)"
  if [ "${STATE}" = "succeeded" ]; then
    break
  fi
  if [ "${STATE}" = "failed" ] || [ "${STATE}" = "canceled" ]; then
    cat "${TASK_POLL_RESPONSE}" >&2
    curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}/events" >&2 || true
    exit 1
  fi
  if [ "${STATE}" = "queued" ] && [ "${i}" -eq 15 ]; then
    echo "Task is still queued after 15 polls; local Worker may not be running." >&2
  fi
  sleep "${SLEEP_SECONDS}"
done

FINAL_STATE="$("${PYTHON_BIN}" - "${TASK_POLL_RESPONSE}" <<'PY'
import json
import sys

print(json.load(open(sys.argv[1], encoding="utf-8")).get("state"))
PY
)"
if [ "${FINAL_STATE}" != "succeeded" ]; then
  echo "Task did not finish within polling window." >&2
  cat "${TASK_POLL_RESPONSE}" >&2
  exit 1
fi

curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}/download-link" >"${DOWNLOAD_RESPONSE}"
DOWNLOAD_URL="$("${PYTHON_BIN}" - "${DOWNLOAD_RESPONSE}" <<'PY'
import json
import sys

url = json.load(open(sys.argv[1], encoding="utf-8"))["url"]
assert "host.docker.internal:9000" not in url
print(url)
PY
)"

curl -fL "${DOWNLOAD_URL}" -o "${DOWNLOAD_OUTPUT}"
BYTES="$(wc -c <"${DOWNLOAD_OUTPUT}" | tr -d ' ')"
if [ "${BYTES}" -le 0 ]; then
  echo "Downloaded file is empty." >&2
  exit 1
fi

rm -f "${DOWNLOAD_OUTPUT}"
echo "Bilibili Chrome smoke passed, downloaded ${BYTES} bytes"
