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
wechat_version=$(env_value WECHAT_CHANNELS_COOKIE_VERSION)
wechat_attested=$(env_value WECHAT_CHANNELS_OPERATOR_ACCOUNT_BASELINE_ATTESTED)
tiktok_provider=$(env_value OPERATOR_PROVIDER_KEY)
tiktok_version=$(env_value OPERATOR_COOKIE_VERSION)
tiktok_attested=$(env_value OPERATOR_ACCOUNT_BASELINE_ATTESTED)
douyin_version=$(env_value DOUYIN_COOKIE_VERSION)
douyin_attested=$(env_value DOUYIN_OPERATOR_ACCOUNT_BASELINE_ATTESTED)
xiaohongshu_version=$(env_value XIAOHONGSHU_COOKIE_VERSION)
xiaohongshu_attested=$(env_value XIAOHONGSHU_OPERATOR_ACCOUNT_BASELINE_ATTESTED)
reddit_version=$(env_value REDDIT_COOKIE_VERSION)
reddit_attested=$(env_value REDDIT_OPERATOR_ACCOUNT_BASELINE_ATTESTED)
x_version=$(env_value X_COOKIE_VERSION)
x_attested=$(env_value X_OPERATOR_ACCOUNT_BASELINE_ATTESTED)
instagram_version=$(env_value INSTAGRAM_COOKIE_VERSION)
instagram_attested=$(env_value INSTAGRAM_OPERATOR_ACCOUNT_BASELINE_ATTESTED)
analysis_enabled=$(env_value ANALYSIS_ENABLED)

set -- docker compose --env-file "$env_file" -f "$compose_file"

case "$operator_urls" in
  *'"youtube"'*) youtube_configured=true ;;
  *) youtube_configured=false ;;
esac

case "$operator_urls" in
  *'"wechat_channels"'*) wechat_configured=true ;;
  *) wechat_configured=false ;;
esac

case "$operator_urls" in
  *'"tiktok"'*) tiktok_configured=true ;;
  *) tiktok_configured=false ;;
esac

case "$operator_urls" in
  *'"douyin"'*) douyin_configured=true ;;
  *) douyin_configured=false ;;
esac

case "$operator_urls" in
  *'"xiaohongshu"'*) xiaohongshu_configured=true ;;
  *) xiaohongshu_configured=false ;;
esac

case "$operator_urls" in
  *'"reddit"'*) reddit_configured=true ;;
  *) reddit_configured=false ;;
esac

case "$operator_urls" in
  *'"x"'*) x_configured=true ;;
  *) x_configured=false ;;
esac

case "$operator_urls" in
  *'"instagram"'*) instagram_configured=true ;;
  *) instagram_configured=false ;;
esac

if [ "$youtube_configured" = true ]; then
  if [ "$youtube_attested" != true ]; then
    echo "YouTube operator route requires its account baseline attestation." >&2
    exit 1
  fi
  youtube_version=${youtube_version:-browser-live}
  export YOUTUBE_COOKIE_VERSION="$youtube_version"
  case "$youtube_version" in
    browser-*) "$script_dir/provider-session-broker.sh" youtube start ;;
  esac
  set -- "$@" --profile youtube-operator
  echo "YouTube browser-session fallback enabled."
fi

if [ "$wechat_configured" = true ]; then
  if [ "$wechat_attested" != true ]; then
    echo "WeChat Channels route requires its account baseline attestation." >&2
    exit 1
  fi
  wechat_version=${wechat_version:-browser-live}
  export WECHAT_CHANNELS_COOKIE_VERSION="$wechat_version"
  case "$wechat_version" in
    browser-*) "$script_dir/provider-session-broker.sh" wechat_channels start ;;
  esac
  set -- "$@" --profile wechat-channels-operator
  echo "WeChat Channels public-link resolver enabled."
fi

if [ "$tiktok_configured" = true ]; then
  if [ "$tiktok_provider" != tiktok ] || [ "$tiktok_attested" != true ]; then
    echo "TikTok route requires its isolated runner and account attestation." >&2
    exit 1
  fi
  tiktok_version=${tiktok_version:-browser-live}
  export OPERATOR_COOKIE_VERSION="$tiktok_version"
  case "$tiktok_version" in
    browser-*) "$script_dir/provider-session-broker.sh" tiktok start ;;
  esac
  set -- "$@" --profile provider-operator
  echo "TikTok browser-session fallback enabled."
fi

if [ "$douyin_configured" = true ]; then
  if [ "$douyin_attested" != true ]; then
    echo "Douyin route requires its account baseline attestation." >&2
    exit 1
  fi
  douyin_version=${douyin_version:-browser-live}
  export DOUYIN_COOKIE_VERSION="$douyin_version"
  case "$douyin_version" in
    browser-*) "$script_dir/provider-session-broker.sh" douyin start ;;
  esac
  set -- "$@" --profile douyin-operator
  echo "Douyin browser-session fallback enabled."
fi

if [ "$xiaohongshu_configured" = true ]; then
  if [ "$xiaohongshu_attested" != true ]; then
    echo "Xiaohongshu route requires its account baseline attestation." >&2
    exit 1
  fi
  xiaohongshu_version=${xiaohongshu_version:-browser-live}
  export XIAOHONGSHU_COOKIE_VERSION="$xiaohongshu_version"
  case "$xiaohongshu_version" in
    browser-*) "$script_dir/provider-session-broker.sh" xiaohongshu start ;;
  esac
  set -- "$@" --profile xiaohongshu-operator
  echo "Xiaohongshu browser-session fallback enabled."
fi

if [ "$reddit_configured" = true ]; then
  if [ "$reddit_attested" != true ]; then
    echo "Reddit route requires its account baseline attestation." >&2
    exit 1
  fi
  reddit_version=${reddit_version:-browser-live}
  export REDDIT_COOKIE_VERSION="$reddit_version"
  case "$reddit_version" in
    browser-*) "$script_dir/provider-session-broker.sh" reddit start ;;
  esac
  set -- "$@" --profile reddit-operator
  echo "Reddit browser-session fallback enabled."
fi

if [ "$x_configured" = true ]; then
  if [ "$x_attested" != true ]; then
    echo "X route requires its account baseline attestation." >&2
    exit 1
  fi
  x_version=${x_version:-browser-live}
  export X_COOKIE_VERSION="$x_version"
  case "$x_version" in
    browser-*) "$script_dir/provider-session-broker.sh" x start ;;
  esac
  set -- "$@" --profile x-operator
  echo "X browser-session fallback enabled."
fi

if [ "$instagram_configured" = true ]; then
  if [ "$instagram_attested" != true ]; then
    echo "Instagram route requires its account baseline attestation." >&2
    exit 1
  fi
  instagram_version=${instagram_version:-browser-live}
  export INSTAGRAM_COOKIE_VERSION="$instagram_version"
  case "$instagram_version" in
    browser-*) "$script_dir/provider-session-broker.sh" instagram start ;;
  esac
  set -- "$@" --profile instagram-operator
  echo "Instagram browser-session fallback enabled."
fi

"$@" up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300

if [ "${analysis_enabled:-true}" = true ]; then
  "$script_dir/analysis-worker.sh" start
fi
