#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
env_file="$project_dir/.env"
compose_file="$project_dir/docker-compose.yml"

if [ ! -f "$env_file" ]; then
  echo "Missing $env_file; copy .env.example and configure local services first." >&2
  exit 1
fi

env_value() {
  sed -n "s/^$1=//p" "$env_file" | tail -n 1
}

operator_urls=$(env_value RUNNER_OPERATOR_BASE_URLS)
youtube_version=$(env_value YOUTUBE_COOKIE_VERSION)
youtube_attested=$(env_value YOUTUBE_OPERATOR_ACCOUNT_BASELINE_ATTESTED)

set -- docker compose --env-file "$env_file" -f "$compose_file"

case "$operator_urls" in
  *'"youtube"'*) youtube_configured=true ;;
  *) youtube_configured=false ;;
esac

if [ "$youtube_configured" = true ] && \
  [ -n "$youtube_version" ] && \
  [ "$youtube_attested" = true ]; then
  case "$youtube_version" in
    browser-*) "$script_dir/youtube-cookie-bridge.sh" start ;;
  esac
  set -- "$@" --profile youtube-operator
  echo "YouTube browser-session fallback enabled."
fi

exec "$@" up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
