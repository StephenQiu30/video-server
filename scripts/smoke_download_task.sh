#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SAMPLE_URL="${SAMPLE_URL:-https://commons.wikimedia.org/wiki/File:%22Movbild-fizika%22_falo_en_Big_Buck_Bunny.webm}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MAX_POLLS="${MAX_POLLS:-60}"

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

cancel_active_tasks

TASK_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"${SAMPLE_URL}\",\"format_id\":\"best\",\"title\":\"[Smoke] Download Acceptance\",\"format_label\":\"best\"}" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

STATE="queued"
for _ in $(seq 1 "${MAX_POLLS}"); do
  PAYLOAD="$(
    curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}"
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

DOWNLOAD_URL="$(
  curl -fsS "${BASE_URL}/api/tasks/${TASK_ID}/download-link" \
    | "${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["url"])'
)"

case "${DOWNLOAD_URL}" in
  *host.docker.internal*|*":9000/"*)
    echo "Expected backend proxy download URL, got object storage URL: ${DOWNLOAD_URL}" >&2
    exit 1
    ;;
esac

TMP_FILE="$(mktemp /tmp/stephen-video-download.XXXXXX)"
curl -fsS "${DOWNLOAD_URL}" -o "${TMP_FILE}"
BYTES="$(wc -c < "${TMP_FILE}" | tr -d ' ')"
rm -f "${TMP_FILE}"
if [ "${BYTES}" -le 0 ]; then
  echo "Expected downloaded file bytes, got ${BYTES}" >&2
  exit 1
fi

FORGED_URL="$(
  "${PYTHON_BIN}" -c 'import sys; print(sys.argv[1].replace("signature=", "signature=bad", 1))' "${DOWNLOAD_URL}"
)"
FORGED_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "${FORGED_URL}")"
if [ "${FORGED_STATUS}" != "403" ]; then
  echo "Expected forged signed download URL to return 403, got ${FORGED_STATUS}" >&2
  exit 1
fi

echo "Download task smoke passed: ${TASK_ID} (${BYTES} bytes)"
