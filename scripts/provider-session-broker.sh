#!/bin/sh
set -eu

umask 077
provider=${1:-}
action=${2:-status}
case "$provider" in
  youtube|wechat_channels|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook) ;;
  *)
    echo "Usage: $0 {youtube|wechat_channels|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook} {start|stop|restart|status}" >&2
    exit 2
    ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
secret_dir="$project_dir/.provider-secrets/$provider"
state_dir="$project_dir/.provider-sessions/$provider"
pid_file="$state_dir/session-broker.pid"
status_file="$state_dir/status.json"
plist_file="$state_dir/launch-agent.plist"
env_file="$project_dir/.env"

case "$provider" in
  youtube)
    version_variable=YOUTUBE_COOKIE_VERSION
    interval_variable=YOUTUBE_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  wechat_channels)
    version_variable=WECHAT_CHANNELS_COOKIE_VERSION
    interval_variable=WECHAT_CHANNELS_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  tiktok)
    version_variable=OPERATOR_COOKIE_VERSION
    interval_variable=TIKTOK_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  douyin)
    version_variable=DOUYIN_COOKIE_VERSION
    interval_variable=DOUYIN_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  xiaohongshu)
    version_variable=XIAOHONGSHU_COOKIE_VERSION
    interval_variable=XIAOHONGSHU_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  reddit)
    version_variable=REDDIT_COOKIE_VERSION
    interval_variable=REDDIT_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  x)
    version_variable=X_COOKIE_VERSION
    interval_variable=X_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  instagram)
    version_variable=INSTAGRAM_COOKIE_VERSION
    interval_variable=INSTAGRAM_SESSION_BROKER_INTERVAL_SECONDS
    ;;
  facebook)
    version_variable=FACEBOOK_COOKIE_VERSION
    interval_variable=FACEBOOK_SESSION_BROKER_INTERVAL_SECONDS
    ;;
esac
cookie_version=$(printenv "$version_variable" 2>/dev/null || true)
interval_seconds=$(printenv "$interval_variable" 2>/dev/null || true)
interval_seconds=${interval_seconds:-15}
if [ -z "$cookie_version" ] && [ -f "$env_file" ]; then
  cookie_version=$(sed -n "s/^${version_variable}=//p" "$env_file" | tail -n 1)
fi
cookie_version=${cookie_version:-browser-live}
case "$cookie_version" in
  *[!A-Za-z0-9._-]*|'')
    echo "Invalid $provider Cookie version." >&2
    exit 2
    ;;
esac

cookie_file="$secret_dir/$cookie_version.cookies.txt"
launchd_label="com.stephenqiu.video.$provider-session-broker"
status_wait_attempts=20
if [ "$(uname -s)" = "Darwin" ]; then
  user_runtime_dir=$(getconf DARWIN_USER_TEMP_DIR)
  log_file="${user_runtime_dir%/}/video-server-$provider-session-broker.log"
else
  log_file="$state_dir/session-broker.log"
fi

broker_command_matches() {
  broker_pid=$1
  command=$(ps -p "$broker_pid" -o command= 2>/dev/null || true)
  case "$command" in
    *app.runner.provider_session_broker*--provider*"$provider"*--interval-seconds*)
      return 0
      ;;
    *) return 1 ;;
  esac
}

broker_process_is_running() {
  if [ "$(uname -s)" = "Darwin" ]; then
    broker_process_state=$(launchctl print "gui/$(id -u)/$launchd_label" 2>/dev/null || true)
    printf '%s\n' "$broker_process_state" | grep -q 'state = running'
    return $?
  fi
  [ -f "$pid_file" ] || return 1
  broker_pid=$(sed -n '1p' "$pid_file")
  [ -n "$broker_pid" ] && kill -0 "$broker_pid" 2>/dev/null && \
    broker_command_matches "$broker_pid"
}

broker_status_is_fresh() {
  [ -f "$status_file" ] &&
    [ -n "$(find "$status_file" -mmin -2 -print -quit 2>/dev/null)" ]
}

broker_state() {
  sed -n 's/.*"state":"\([a-z_]*\)".*/\1/p' "$status_file" 2>/dev/null | head -n 1
}

broker_version() {
  sed -n 's/.*"version":"\([A-Za-z0-9._-]*\)".*/\1/p' "$status_file" 2>/dev/null | head -n 1
}

broker_configuration_matches() {
  [ "$(broker_version)" = "$cookie_version" ]
}

broker_is_ready() {
  broker_status_is_fresh && [ "$(broker_state)" = ready ] && [ -f "$cookie_file" ]
}

wait_for_broker_status() {
  attempts=0
  while [ "$attempts" -lt "$status_wait_attempts" ]; do
    if broker_process_is_running && broker_status_is_fresh && \
      broker_configuration_matches; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.5
  done
  return 1
}

unload_launch_agent() {
  launchctl bootout "gui/$(id -u)/$launchd_label" >/dev/null 2>&1 || true
  attempts=0
  while [ "$attempts" -lt 20 ]; do
    if ! launchctl print "gui/$(id -u)/$launchd_label" >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.1
  done
  return 1
}

bootstrap_launch_agent() {
  attempts=0
  while [ "$attempts" -lt 20 ]; do
    if launchctl bootstrap "gui/$(id -u)" "$plist_file" >/dev/null 2>&1; then
      return 0
    fi
    if launchctl print "gui/$(id -u)/$launchd_label" >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.1
  done
  launchctl bootstrap "gui/$(id -u)" "$plist_file"
}

stop_broker() {
  if [ "$(uname -s)" = "Darwin" ]; then
    if launchctl print "gui/$(id -u)/$launchd_label" >/dev/null 2>&1; then
      unload_launch_agent
      echo "$provider Session Broker stopped."
    else
      echo "$provider Session Broker is not running."
    fi
    return
  fi
  if ! broker_process_is_running; then
    rm -f "$pid_file"
    echo "$provider Session Broker is not running."
    return
  fi
  broker_pid=$(sed -n '1p' "$pid_file")
  kill "$broker_pid"
  rm -f "$pid_file"
  echo "$provider Session Broker stopped."
}

start_broker() {
  mkdir -p "$secret_dir" "$state_dir"
  chmod 700 "$project_dir/.provider-secrets" "$secret_dir" \
    "$project_dir/.provider-sessions" "$state_dir"
  touch "$log_file"
  chmod 600 "$log_file"
  if broker_process_is_running && broker_status_is_fresh && \
    broker_configuration_matches; then
    echo "$provider Session Broker is already running (state=$(broker_state))."
    return
  fi
  if broker_process_is_running; then
    echo "$provider Session Broker status is stale; restarting it."
    stop_broker
  fi
  rm -f "$pid_file"
  if [ "$(uname -s)" = "Darwin" ]; then
    python_bin="$project_dir/backend/.venv/bin/python"
    if [ ! -x "$python_bin" ]; then
      (cd "$project_dir/backend" && uv sync --frozen --dev)
    fi
    "$python_bin" -m app.runner.provider_session_launchd \
      --project "$project_dir" \
      --provider "$provider" \
      --version "$cookie_version" \
      --interval-seconds "$interval_seconds" \
      --output "$plist_file" \
      --log "$log_file"
    unload_launch_agent
    bootstrap_launch_agent
    launchctl kickstart -k "gui/$(id -u)/$launchd_label"
    if ! wait_for_broker_status; then
      echo "$provider Session Broker failed to publish status; inspect its scoped log."
      exit 1
    fi
    echo "$provider Session Broker started (state=$(broker_state))."
    return
  fi
  cd "$project_dir/backend"
  nohup uv run python -m app.runner.provider_session_broker \
    --provider "$provider" \
    --browser chrome \
    --version "$cookie_version" \
    --output-root ../.provider-secrets \
    --status-path "../.provider-sessions/$provider/status.json" \
    --interval-seconds "$interval_seconds" \
    >>"$log_file" 2>&1 &
  broker_pid=$!
  printf '%s\n' "$broker_pid" >"$pid_file"
  chmod 600 "$pid_file" "$log_file"
  if ! wait_for_broker_status; then
    echo "$provider Session Broker failed to publish status; inspect its scoped log."
    exit 1
  fi
  echo "$provider Session Broker started (state=$(broker_state))."
}

case "$action" in
  start) start_broker ;;
  stop) stop_broker ;;
  restart)
    stop_broker
    start_broker
    ;;
  status)
    if broker_process_is_running && broker_configuration_matches && \
      broker_is_ready; then
      echo "$provider Session Broker is ready."
    elif broker_process_is_running && broker_configuration_matches; then
      echo "$provider Session Broker is running (state=$(broker_state))."
      exit 1
    elif broker_process_is_running; then
      echo "$provider Session Broker configuration is stale."
      exit 1
    else
      echo "$provider Session Broker is not running."
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 {youtube|wechat_channels|tiktok|douyin|xiaohongshu|reddit|x|instagram|facebook} {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
