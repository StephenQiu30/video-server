#!/bin/sh
set -eu

umask 077
action=${1:-status}
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
state_dir="$project_dir/.local-runtime/analysis-worker"
pid_file="$state_dir/worker.pid"
plist_file="$state_dir/launch-agent.plist"
env_file="$project_dir/.env"
launchd_label=com.stephenqiu.video.analysis-worker

env_value() {
  sed -n "s/^$1=//p" "$env_file" | tail -n 1
}

provider=$(env_value ANALYSIS_CLI_PROVIDER)
provider=${provider:-codex}
case "$provider" in
  codex) binary=$(env_value ANALYSIS_CODEX_BINARY); binary=${binary:-codex} ;;
  claude) binary=$(env_value ANALYSIS_CLAUDE_BINARY); binary=${binary:-claude} ;;
  *) echo "Unsupported analysis CLI provider: $provider" >&2; exit 2 ;;
esac

case "$binary" in
  /*) cli_binary=$binary ;;
  *) cli_binary=$(command -v "$binary" 2>/dev/null || true) ;;
esac
if [ -z "$cli_binary" ] || [ ! -x "$cli_binary" ]; then
  echo "$provider CLI is not available for the analysis worker." >&2
  exit 1
fi

if [ "$(uname -s)" = Darwin ]; then
  user_runtime_dir=$(getconf DARWIN_USER_TEMP_DIR)
  log_file="${user_runtime_dir%/}/video-server-analysis-worker.log"
else
  log_file="$state_dir/worker.log"
fi

worker_is_running() {
  if [ "$(uname -s)" = Darwin ]; then
    state=$(launchctl print "gui/$(id -u)/$launchd_label" 2>/dev/null || true)
    printf '%s\n' "$state" | grep -q 'state = running'
    return $?
  fi
  [ -f "$pid_file" ] || return 1
  pid=$(sed -n '1p' "$pid_file")
  command=$(ps -p "$pid" -o command= 2>/dev/null || true)
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && \
    printf '%s\n' "$command" | grep -q 'app.workers.analysis.main'
}

stop_worker() {
  if [ "$(uname -s)" = Darwin ]; then
    launchctl bootout "gui/$(id -u)/$launchd_label" >/dev/null 2>&1 || true
  elif worker_is_running; then
    pid=$(sed -n '1p' "$pid_file")
    kill "$pid"
  fi
  rm -f "$pid_file"
}

start_worker() {
  mkdir -p "$state_dir"
  chmod 700 "$project_dir/.local-runtime" "$state_dir"
  touch "$log_file"
  chmod 600 "$log_file"
  if worker_is_running; then
    echo "Analysis worker is already running."
    return
  fi
  python_bin="$project_dir/backend/.venv/bin/python"
  if [ ! -x "$python_bin" ]; then
    (cd "$project_dir/backend" && uv sync --frozen --dev)
  fi
  if [ "$(uname -s)" = Darwin ]; then
    "$python_bin" -m app.workers.analysis.launchd \
      --project "$project_dir" \
      --cli-binary "$cli_binary" \
      --output "$plist_file" \
      --log "$log_file"
    launchctl bootout "gui/$(id -u)/$launchd_label" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$plist_file"
    launchctl kickstart -k "gui/$(id -u)/$launchd_label"
  else
    cd "$project_dir/backend"
    nohup "$python_bin" -m app.workers.analysis.main >>"$log_file" 2>&1 &
    printf '%s\n' "$!" >"$pid_file"
    chmod 600 "$pid_file"
  fi
  attempts=0
  while [ "$attempts" -lt 20 ]; do
    if worker_is_running; then
      echo "Analysis worker started under system supervision."
      return
    fi
    attempts=$((attempts + 1))
    sleep 0.5
  done
  echo "Analysis worker failed to stay running; inspect its scoped log." >&2
  exit 1
}

case "$action" in
  start) start_worker ;;
  stop) stop_worker; echo "Analysis worker stopped." ;;
  restart) stop_worker; start_worker ;;
  status)
    if worker_is_running; then
      echo "Analysis worker is running."
    else
      echo "Analysis worker is not running."
      exit 1
    fi
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}" >&2; exit 2 ;;
esac
