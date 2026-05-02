#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="${PYTHONPATH:-}:apps/api:apps/worker:packages/shared"

"${PYTHON_BIN}" -m pytest apps/api/tests
