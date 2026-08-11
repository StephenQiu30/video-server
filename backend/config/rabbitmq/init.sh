#!/bin/sh
set -eu

: "${RABBITMQ_QUEUE_TYPE:=classic}"
: "${RABBITMQ_MESSAGE_TTL_MS:=86400000}"
: "${RABBITMQ_MAX_LENGTH:=10000}"
: "${RABBITMQ_MAX_LENGTH_BYTES:=268435456}"
: "${RABBITMQ_DELIVERY_LIMIT:=5}"
: "${RABBITMQ_DLQ_MAX_LENGTH:=10000}"
: "${RABBITMQ_DLQ_MAX_LENGTH_BYTES:=268435456}"
: "${RABBITMQ_MIGRATE_LEGACY_QUEUE_ARGUMENTS:=false}"

for value in \
  "$RABBITMQ_ADMIN_USER" "$RABBITMQ_ADMIN_PASS" \
  "$RABBITMQ_API_USER" "$RABBITMQ_API_PASS" \
  "$RABBITMQ_OUTBOX_USER" "$RABBITMQ_OUTBOX_PASS" \
  "$RABBITMQ_DOWNLOAD_USER" "$RABBITMQ_DOWNLOAD_PASS" \
  "$RABBITMQ_ANALYSIS_USER" "$RABBITMQ_ANALYSIS_PASS" \
  "$RABBITMQ_REPORT_USER" "$RABBITMQ_REPORT_PASS" \
  "$RABBITMQ_DLQ_USER" "$RABBITMQ_DLQ_PASS"; do
  case "$value" in ''|*[!A-Za-z0-9._~-]*) exit 2 ;; esac
done
case "$RABBITMQ_VHOST" in ''|*[!A-Za-z0-9._~-]*) exit 2 ;; esac
case "$RABBITMQ_QUEUE_TYPE" in classic|quorum) ;; *) exit 2 ;; esac
case "$RABBITMQ_MIGRATE_LEGACY_QUEUE_ARGUMENTS" in true|false) ;; *) exit 2 ;; esac
for value in \
  "$RABBITMQ_MESSAGE_TTL_MS" "$RABBITMQ_MAX_LENGTH" \
  "$RABBITMQ_MAX_LENGTH_BYTES" "$RABBITMQ_DELIVERY_LIMIT" \
  "$RABBITMQ_DLQ_MAX_LENGTH" "$RABBITMQ_DLQ_MAX_LENGTH_BYTES"; do
  case "$value" in ''|*[!0-9]*|0) exit 2 ;; esac
done

api="http://rabbitmq:15672/api"
auth="$RABBITMQ_ADMIN_USER:$RABBITMQ_ADMIN_PASS"
until curl -fsS -u "$auth" "$api/overview" >/dev/null; do sleep 1; done

put() {
  curl -fsS -u "$auth" -H 'content-type: application/json' \
    -X PUT "$api/$1" --data "$2" >/dev/null
}
post() {
  curl -fsS -u "$auth" -H 'content-type: application/json' \
    -X POST "$api/$1" --data "$2" >/dev/null
}
exists() {
  curl -fsS -u "$auth" "$api/$1" >/dev/null 2>&1
}
delete_if_empty() {
  curl -fsS -u "$auth" -X DELETE \
    "$api/$1?if-empty=true&if-unused=true" >/dev/null 2>&1
}
create_user() {
  user="$1"; password="$2"; configure="$3"; write="$4"; read="$5"
  put "users/$user" "{\"password\":\"$password\",\"tags\":\"\"}"
  put "permissions/$RABBITMQ_VHOST/$user" \
    "{\"configure\":\"$configure\",\"write\":\"$write\",\"read\":\"$read\"}"
}

put "vhosts/$RABBITMQ_VHOST" '{}'
create_user "$RABBITMQ_API_USER" "$RABBITMQ_API_PASS" '^amq[._-].*$' '^amq[._-].*$' '^(amq[._-].*|video\\.events)$'
create_user "$RABBITMQ_OUTBOX_USER" "$RABBITMQ_OUTBOX_PASS" '^$' '^video\\.events$' '^$'
create_user "$RABBITMQ_DOWNLOAD_USER" "$RABBITMQ_DOWNLOAD_PASS" '^$' '^$' '^video\\.download$'
create_user "$RABBITMQ_ANALYSIS_USER" "$RABBITMQ_ANALYSIS_PASS" '^$' '^$' '^video\\.analysis$'
create_user "$RABBITMQ_REPORT_USER" "$RABBITMQ_REPORT_PASS" '^$' '^$' '^video\\.analysis-report$'
create_user "$RABBITMQ_DLQ_USER" "$RABBITMQ_DLQ_PASS" '^$' '^video\\.events$' '^video\\.(download|analysis|analysis-report)\\.dead$'

# Topic permissions prevent the Gateway's exchange binding permission from
# becoming publish permission, and bound DLQ replays to command routing keys.
put "topic-permissions/$RABBITMQ_VHOST/$RABBITMQ_API_USER" \
  '{"exchange":"video.events","write":"^$","read":"^task\\.state\\.changed$"}'
put "topic-permissions/$RABBITMQ_VHOST/$RABBITMQ_OUTBOX_USER" \
  '{"exchange":"video.events","write":"^(download\\.requested|analysis\\.requested|analysis\\.report\\.publish\\.requested|task\\.state\\.changed)$","read":"^$"}'
put "topic-permissions/$RABBITMQ_VHOST/$RABBITMQ_DLQ_USER" \
  '{"exchange":"video.events","write":"^(download\\.requested|analysis\\.requested|analysis\\.report\\.publish\\.requested)$","read":"^$"}'

put "exchanges/$RABBITMQ_VHOST/video.events" \
  '{"type":"topic","durable":true,"auto_delete":false,"internal":false,"arguments":{}}'
put "exchanges/$RABBITMQ_VHOST/video.events.dead" \
  '{"type":"direct","durable":true,"auto_delete":false,"internal":false,"arguments":{}}'

source_policy() {
  policy_name="$1"; policy_pattern="$2"; dead_target="$3"
  policy_definition="{\"dead-letter-exchange\":\"video.events.dead\",\"dead-letter-routing-key\":\"$dead_target\",\"message-ttl\":$RABBITMQ_MESSAGE_TTL_MS,\"max-length\":$RABBITMQ_MAX_LENGTH,\"max-length-bytes\":$RABBITMQ_MAX_LENGTH_BYTES,\"overflow\":\"reject-publish\"}"
  if [ "$RABBITMQ_QUEUE_TYPE" = quorum ]; then
    policy_definition="{\"dead-letter-exchange\":\"video.events.dead\",\"dead-letter-routing-key\":\"$dead_target\",\"dead-letter-strategy\":\"at-least-once\",\"delivery-limit\":$RABBITMQ_DELIVERY_LIMIT,\"message-ttl\":$RABBITMQ_MESSAGE_TTL_MS,\"max-length\":$RABBITMQ_MAX_LENGTH,\"max-length-bytes\":$RABBITMQ_MAX_LENGTH_BYTES,\"overflow\":\"reject-publish\"}"
  fi
  put "policies/$RABBITMQ_VHOST/$policy_name" \
    "{\"pattern\":\"$policy_pattern\",\"definition\":$policy_definition,\"priority\":20,\"apply-to\":\"queues\"}"
}

source_policy video-download-reliability '^video\\.download$' video.download.dead
source_policy video-analysis-reliability '^video\\.analysis$' video.analysis.dead
source_policy video-analysis-report-reliability '^video\\.analysis-report$' video.analysis-report.dead
put "policies/$RABBITMQ_VHOST/video-dead-letter-retention" \
  "{\"pattern\":\"^video\\\\.(download|analysis|analysis-report)\\\\.dead$\",\"definition\":{\"max-length\":$RABBITMQ_DLQ_MAX_LENGTH,\"max-length-bytes\":$RABBITMQ_DLQ_MAX_LENGTH_BYTES,\"overflow\":\"drop-head\"},\"priority\":20,\"apply-to\":\"queues\"}"

ensure_queue() {
  candidate_queue="$1"; allow_migrate="$2"
  if exists "queues/$RABBITMQ_VHOST/$candidate_queue"; then
    if [ "$allow_migrate" != true ] || [ "$RABBITMQ_MIGRATE_LEGACY_QUEUE_ARGUMENTS" != true ]; then
      return
    fi
    if ! delete_if_empty "queues/$RABBITMQ_VHOST/$candidate_queue"; then
      echo "queue $candidate_queue is in use or non-empty; legacy arguments were not migrated" >&2
      return
    fi
  fi
  put "queues/$RABBITMQ_VHOST/$candidate_queue" \
    "{\"durable\":true,\"auto_delete\":false,\"arguments\":{\"x-queue-type\":\"$RABBITMQ_QUEUE_TYPE\"}}"
}

declare_queue() {
  main_queue="$1"; main_route="$2"
  dead_queue="$main_queue.dead"
  ensure_queue "$dead_queue" false
  ensure_queue "$main_queue" true
  post "bindings/$RABBITMQ_VHOST/e/video.events/q/$main_queue" \
    "{\"routing_key\":\"$main_route\",\"arguments\":{}}"
  post "bindings/$RABBITMQ_VHOST/e/video.events.dead/q/$dead_queue" \
    "{\"routing_key\":\"$dead_queue\",\"arguments\":{}}"
}

declare_queue video.download download.requested
declare_queue video.analysis analysis.requested
declare_queue video.analysis-report analysis.report.publish.requested
