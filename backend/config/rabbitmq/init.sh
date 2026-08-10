#!/bin/sh
set -eu

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

declare_queue() {
  queue="$1"; route="$2"
  dead="$queue.dead"
  put "queues/$RABBITMQ_VHOST/$dead" \
    '{"durable":true,"auto_delete":false,"arguments":{}}'
  put "queues/$RABBITMQ_VHOST/$queue" \
    "{\"durable\":true,\"auto_delete\":false,\"arguments\":{\"x-dead-letter-exchange\":\"video.events.dead\",\"x-dead-letter-routing-key\":\"$dead\",\"x-message-ttl\":1800000,\"x-max-length\":10000,\"x-overflow\":\"reject-publish-dlx\"}}"
  post "bindings/$RABBITMQ_VHOST/e/video.events/q/$queue" \
    "{\"routing_key\":\"$route\",\"arguments\":{}}"
  post "bindings/$RABBITMQ_VHOST/e/video.events.dead/q/$dead" \
    "{\"routing_key\":\"$dead\",\"arguments\":{}}"
}

declare_queue video.download download.requested
declare_queue video.analysis analysis.requested
declare_queue video.analysis-report analysis.report.publish.requested
