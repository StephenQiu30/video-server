#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$script_dir/provider-cookie-bridge.sh" youtube "${1:-status}"
