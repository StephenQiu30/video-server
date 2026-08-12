#!/usr/bin/env bash
set -Eeuo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
environment_file=$(mktemp "${TMPDIR:-/tmp}/video-server-ci.XXXXXX")
compose=(
  docker compose
  --project-name video-server-ci
  --env-file "$environment_file"
  -f "$repository_root/docker-compose.yml"
  --profile environment
)
started=0

cleanup() {
  status=$?
  trap - EXIT
  if ((status != 0 && started == 1)); then
    "${compose[@]}" ps --all || true
    "${compose[@]}" logs --no-color --tail=200 || true
  fi
  if ((started == 1)); then
    "${compose[@]}" down --volumes --remove-orphans || true
  fi
  rm -f "$environment_file"
  exit "$status"
}
trap cleanup EXIT

cp "$repository_root/.env.example" "$environment_file"
export ANALYSIS_ENABLED=false

cd "$repository_root"
conflicts=()
while IFS= read -r container_name; do
  if docker inspect "$container_name" >/dev/null 2>&1; then
    conflicts+=("$container_name")
  fi
done < <(
  "${compose[@]}" config --format json |
    python3 -c 'import json,sys; print("\n".join(sorted(service["container_name"] for service in json.load(sys.stdin)["services"].values())))'
)
if ((${#conflicts[@]} > 0)); then
  printf '运行边界烟测拒绝复用或删除已有同名容器：%s\n' "${conflicts[*]}" >&2
  printf '请先自行停止并移除对应项目，再重新执行。\n' >&2
  exit 2
fi

docker build --target runtime --tag video-server:local .
started=1
"${compose[@]}" up \
  --detach \
  database-init rabbitmq-init valkey minio-init
initializer_statuses=$(docker wait database-init rabbitmq-init minio-init)
initializer_count=0
for initializer_status in $initializer_statuses; do
  initializer_count=$((initializer_count + 1))
  if [[ "$initializer_status" != 0 ]]; then
    printf '初始化任务失败，退出码：%s\n' "$initializer_status" >&2
    exit 1
  fi
done
if ((initializer_count != 3)); then
  printf '未能读取全部初始化任务退出状态。\n' >&2
  exit 1
fi
"${compose[@]}" up \
  --detach \
  --wait \
  --wait-timeout 240 \
  postgres rabbitmq valkey minio
"${compose[@]}" up \
  --detach \
  --wait \
  --wait-timeout 240 \
  --no-build \
  api outbox worker-download provider-canary worker-report media-runner

python3 - <<'PY'
import json
import urllib.request


def request(path: str) -> tuple[dict[str, object] | None, str]:
    with urllib.request.urlopen(f"http://127.0.0.1:8101{path}", timeout=10) as response:
        content_type = response.headers.get_content_type()
        body = response.read().decode("utf-8")
        if content_type == "application/json":
            return json.loads(body), content_type
        return None, content_type


live, _ = request("/health/live")
ready, _ = request("/health/ready")
schema, _ = request("/openapi.json")
_, root_content_type = request("/")
assert live == {"status": "ok"}
assert ready == {"status": "ok", "service": "api"}
assert isinstance(schema, dict) and len(schema.get("paths", {})) > 0
assert root_content_type == "text/html"
print(f"运行时烟测通过：{len(schema['paths'])} 个 OpenAPI paths")
PY

"${compose[@]}" run --rm --no-deps database-init

cd "$repository_root/frontend"
npm ci
OPENAPI_SCHEMA_URL=http://127.0.0.1:8101/openapi.json npm run openapi:check
