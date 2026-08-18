#!/bin/sh
set -eu

umask 077
provider=${1:-}
action=${2:-status}
case "$provider" in
  youtube|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook) ;;
  *)
    echo "Usage: $0 {youtube|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook} {start|stop|restart|status}" >&2
    exit 2
    ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
state_dir="$project_dir/.provider-secrets/$provider"
pid_file="$state_dir/browser-cookie-bridge.pid"
env_file="$project_dir/.env"

case "$provider" in
  youtube)
    version_variable=YOUTUBE_COOKIE_VERSION
    interval_variable=YOUTUBE_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  tiktok)
    version_variable=OPERATOR_COOKIE_VERSION
    interval_variable=TIKTOK_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  douyin)
    version_variable=DOUYIN_COOKIE_VERSION
    interval_variable=DOUYIN_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  xiaohongshu)
    version_variable=XIAOHONGSHU_COOKIE_VERSION
    interval_variable=XIAOHONGSHU_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  reddit)
    version_variable=REDDIT_COOKIE_VERSION
    interval_variable=REDDIT_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  x)
    version_variable=X_COOKIE_VERSION
    interval_variable=X_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  instagram)
    version_variable=INSTAGRAM_COOKIE_VERSION
    interval_variable=INSTAGRAM_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
  facebook)
    version_variable=FACEBOOK_COOKIE_VERSION
    interval_variable=FACEBOOK_COOKIE_BRIDGE_INTERVAL_SECONDS
    ;;
esac
cookie_version=$(printenv "$version_variable" 2>/dev/null || true)
interval_seconds=$(printenv "$interval_variable" 2>/dev/null || true)
interval_seconds=${interval_seconds:-15}
if [ -z "$cookie_version" ] && [ -f "$env_file" ]; then
  cookie_version=$(sed -n "s/^${version_variable}=//p" "$env_file" | tail -n 1)
fi
cookie_version=${cookie_version:-browser-v1}
case "$cookie_version" in
  *[!A-Za-z0-9._-]*|'')
    echo "Invalid $provider Cookie version." >&2
    exit 2
    ;;
esac

cookie_file="$state_dir/$cookie_version.cookies.txt"
launchd_label="com.stephenqiu.video.$provider-cookie-bridge"
if [ "$(uname -s)" = "Darwin" ]; then
  user_runtime_dir=$(getconf DARWIN_USER_TEMP_DIR)
  log_file="${user_runtime_dir%/}/video-server-$provider-cookie-bridge.log"
else
  log_file="$state_dir/browser-cookie-bridge.log"
fi

bridge_command_matches() {
  bridge_pid=$1
  command=$(ps -p "$bridge_pid" -o command= 2>/dev/null || true)
  case "$command" in
    *app.runner.browser_cookie_export*--provider*"$provider"*--watch-interval-seconds*)
      return 0
      ;;
    *) return 1 ;;
  esac
}

bridge_status() {
  if [ "$(uname -s)" = "Darwin" ]; then
    bridge_state=$(launchctl print "gui/$(id -u)/$launchd_label" 2>/dev/null || true)
    printf '%s\n' "$bridge_state" | grep -q 'state = running'
    return $?
  fi
  [ -f "$pid_file" ] || return 1
  bridge_pid=$(sed -n '1p' "$pid_file")
  [ -n "$bridge_pid" ] && kill -0 "$bridge_pid" 2>/dev/null && \
    bridge_command_matches "$bridge_pid"
}

bridge_secret_is_fresh() {
  [ -f "$cookie_file" ] &&
    [ -n "$(find "$cookie_file" -mmin -2 -print -quit 2>/dev/null)" ]
}

stop_bridge() {
  if [ "$(uname -s)" = "Darwin" ]; then
    if launchctl print "gui/$(id -u)/$launchd_label" >/dev/null 2>&1; then
      launchctl remove "$launchd_label"
      echo "$provider Cookie bridge stopped."
    else
      echo "$provider Cookie bridge is not running."
    fi
    return
  fi
  if ! bridge_status; then
    rm -f "$pid_file"
    echo "$provider Cookie bridge is not running."
    return
  fi
  bridge_pid=$(sed -n '1p' "$pid_file")
  kill "$bridge_pid"
  rm -f "$pid_file"
  echo "$provider Cookie bridge stopped."
}

start_bridge() {
  mkdir -p "$state_dir"
  chmod 700 "$project_dir/.provider-secrets" "$state_dir"
  touch "$log_file"
  chmod 600 "$log_file"
  if bridge_status && bridge_secret_is_fresh; then
    echo "$provider Cookie bridge is already running."
    return
  fi
  if bridge_status; then
    echo "$provider Cookie bridge snapshot is stale; restarting it."
    stop_bridge
  fi
  rm -f "$pid_file"
  if [ "$(uname -s)" = "Darwin" ]; then
    python_bin="$project_dir/backend/.venv/bin/python"
    if [ ! -x "$python_bin" ]; then
      (cd "$project_dir/backend" && uv sync --frozen --dev)
    fi
    launchctl remove "$launchd_label" >/dev/null 2>&1 || true
    launchctl submit \
      -l "$launchd_label" \
      -o "$log_file" \
      -e "$log_file" \
      -- /bin/sh -c \
      'exec "$1" -m app.runner.browser_cookie_export --provider "$2" --browser chrome --version "$3" --output-root "$4" --watch-interval-seconds "$5"' \
      provider-cookie-bridge "$python_bin" "$provider" "$cookie_version" \
      "$project_dir/.provider-secrets" "$interval_seconds"
    sleep 1
    if ! bridge_status; then
      echo "$provider Cookie bridge failed to start; inspect its scoped log."
      exit 1
    fi
    echo "$provider Cookie bridge started."
    return
  fi
  cd "$project_dir/backend"
  nohup uv run python -m app.runner.browser_cookie_export \
    --provider "$provider" \
    --browser chrome \
    --version "$cookie_version" \
    --output-root ../.provider-secrets \
    --watch-interval-seconds "$interval_seconds" \
    >>"$log_file" 2>&1 &
  bridge_pid=$!
  printf '%s\n' "$bridge_pid" >"$pid_file"
  chmod 600 "$pid_file" "$log_file"
  sleep 1
  if ! bridge_status; then
    echo "$provider Cookie bridge failed to start; inspect its scoped log."
    exit 1
  fi
  echo "$provider Cookie bridge started."
}

case "$action" in
  start) start_bridge ;;
  stop) stop_bridge ;;
  restart)
    stop_bridge
    start_bridge
    ;;
  status)
    if bridge_status && bridge_secret_is_fresh; then
      echo "$provider Cookie bridge is running."
    elif bridge_status; then
      echo "$provider Cookie bridge process is running, but its snapshot is stale."
      exit 1
    else
      echo "$provider Cookie bridge is not running."
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 {youtube|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook} {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
