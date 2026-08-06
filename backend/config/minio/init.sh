#!/bin/sh
set -eu

case "$MINIO_BUCKET" in
  ''|*[!a-z0-9.-]*|.*|*.) exit 2 ;;
esac
[ "$MINIO_ACCESS_KEY" != "$MINIO_ROOT_USER" ]

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$MINIO_BUCKET"
mc anonymous set none "local/$MINIO_BUCKET"
printf '%s\n' \
  '{"Version":"2012-10-17","Statement":[' \
  "{\"Effect\":\"Allow\",\"Action\":[\"s3:GetBucketLocation\",\"s3:ListBucket\"],\"Resource\":[\"arn:aws:s3:::$MINIO_BUCKET\"]}," \
  "{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\",\"s3:DeleteObject\"],\"Resource\":[\"arn:aws:s3:::$MINIO_BUCKET/*\"]}" \
  ']}' > /tmp/app-policy.json
mc admin user add local "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc admin policy create local video-server-app /tmp/app-policy.json
mc admin policy attach local video-server-app --user "$MINIO_ACCESS_KEY"
