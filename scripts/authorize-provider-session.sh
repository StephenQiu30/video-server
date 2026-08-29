#!/bin/sh
set -eu

umask 077
provider=${1:-}
case "$provider" in
  youtube|wechat_channels|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook) ;;
  *)
    echo "Usage: $0 {youtube|wechat_channels|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook}" >&2
    exit 2
    ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
env_file="$project_dir/.env"

env_value() {
  if [ -f "$env_file" ]; then
    sed -n "s/^$1=//p" "$env_file" | tail -n 1
  fi
}

case "$provider" in
  youtube)
    version=$(env_value YOUTUBE_COOKIE_VERSION)
    secret_dir=$(env_value YOUTUBE_COOKIE_SECRET_DIR)
    ;;
  wechat_channels)
    version=$(env_value WECHAT_CHANNELS_COOKIE_VERSION)
    secret_dir=$(env_value WECHAT_CHANNELS_COOKIE_SECRET_DIR)
    ;;
  tiktok)
    version=$(env_value OPERATOR_COOKIE_VERSION)
    secret_dir=$(env_value OPERATOR_COOKIE_SECRET_DIR)
    ;;
  douyin)
    version=$(env_value DOUYIN_COOKIE_VERSION)
    secret_dir=$(env_value DOUYIN_COOKIE_SECRET_DIR)
    ;;
  xiaohongshu)
    version=$(env_value XIAOHONGSHU_COOKIE_VERSION)
    secret_dir=$(env_value XIAOHONGSHU_COOKIE_SECRET_DIR)
    ;;
  reddit)
    version=$(env_value REDDIT_COOKIE_VERSION)
    secret_dir=$(env_value REDDIT_COOKIE_SECRET_DIR)
    ;;
  x)
    version=$(env_value X_COOKIE_VERSION)
    secret_dir=$(env_value X_COOKIE_SECRET_DIR)
    ;;
  instagram)
    version=$(env_value INSTAGRAM_COOKIE_VERSION)
    secret_dir=$(env_value INSTAGRAM_COOKIE_SECRET_DIR)
    ;;
  facebook)
    version=$(env_value FACEBOOK_COOKIE_VERSION)
    secret_dir=$(env_value FACEBOOK_COOKIE_SECRET_DIR)
    ;;
esac
version=${version:-browser-live}
secret_dir=${secret_dir:-./.provider-secrets/$provider}
case "$secret_dir" in
  /*) resolved_secret_dir=$secret_dir ;;
  *) resolved_secret_dir="$project_dir/${secret_dir#./}" ;;
esac
output_root=$(dirname "$resolved_secret_dir")
state_root="$project_dir/.provider-sessions/$provider"
python_bin="$project_dir/backend/.venv/bin/python"

if [ ! -x "$python_bin" ]; then
  (cd "$project_dir/backend" && uv sync --frozen --dev)
fi
cd "$project_dir/backend"
"$python_bin" -m app.runner.provider_session_authorize \
  --provider "$provider" \
  --version "$version" \
  --output-root "$output_root" \
  --state-root "$state_root"
