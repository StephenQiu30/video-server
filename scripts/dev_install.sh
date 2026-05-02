#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_INSTALL_ARGS="${PIP_INSTALL_ARGS:-}"

"${PYTHON_BIN}" -m pip install ${PIP_INSTALL_ARGS} -r apps/api/requirements.txt

echo "依赖已安装到当前本地 Python 环境：$(${PYTHON_BIN} -c 'import sys; print(sys.executable)')"
