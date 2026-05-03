#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="${PYTHONPATH:-apps/api:apps/worker:packages/shared}"

"${PYTHON_BIN}" - <<'PY'
from worker.jobs import cleanup_expired_outputs

removed = cleanup_expired_outputs()
print(f"Expired output cleanup complete: {removed} object(s) removed")
PY
