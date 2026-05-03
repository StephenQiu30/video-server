#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'MESSAGE'
smoke_admin_quota.sh is reserved for the future production-saas-readiness phase.
M1 now runs in local single-user mode and does not mount login or admin APIs.
MESSAGE

exit 2
