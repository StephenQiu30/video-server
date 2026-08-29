#!/bin/sh
set -eu

origins="${MINIO_API_CORS_ALLOW_ORIGIN-}"

invalid_cors() {
  echo "MINIO_CORS_ALLOWED_ORIGINS must contain comma-separated exact HTTP(S) origins without wildcards" >&2
  exit 64
}

case "$origins" in
  ""|","*|*","|*",,"*|*"*"*|*"?"*|*[[:space:]]*) invalid_cors ;;
esac

remaining="$origins"
while :; do
  origin=${remaining%%,*}
  case "$origin" in
    http://*|https://*) ;;
    *) invalid_cors ;;
  esac
  authority=${origin#*://}
  case "$authority" in
    ""|*/*|*@*|*\#*) invalid_cors ;;
  esac
  host="$authority"
  case "$authority" in
    *:*)
      host=${authority%:*}
      port=${authority##*:}
      case "$host" in *:*) invalid_cors ;; esac
      case "$port" in ""|*[!0-9]*|??????*) invalid_cors ;; esac
      if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        invalid_cors
      fi
      ;;
  esac
  case "$host" in
    ""|.*|*.|*..*|*[!A-Za-z0-9.-]*) invalid_cors ;;
  esac
  labels="$host"
  while :; do
    label=${labels%%.*}
    case "$label" in ""|-*|*-|*[!A-Za-z0-9-]*) invalid_cors ;; esac
    if [ "$labels" = "$label" ]; then
      break
    fi
    labels=${labels#*.}
  done
  if [ "$remaining" = "$origin" ]; then
    break
  fi
  remaining=${remaining#*,}
done
