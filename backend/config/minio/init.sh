#!/bin/sh
set -eu

case "$MINIO_BUCKET" in
  ''|*[!a-z0-9.-]*|.*|*.) exit 2 ;;
esac

keys="$MINIO_API_ACCESS_KEY $MINIO_DOWNLOAD_ACCESS_KEY $MINIO_REPORT_ACCESS_KEY $MINIO_ANALYSIS_ACCESS_KEY $MINIO_CANARY_ACCESS_KEY"
for key in $keys; do
  [ "$key" != "$MINIO_ROOT_USER" ]
done
[ "$(printf '%s\n' $keys | sort -u | wc -l | tr -d ' ')" = 5 ]

until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"; do
  sleep 1
done
mc mb --ignore-existing "local/$MINIO_BUCKET"
mc anonymous set none "local/$MINIO_BUCKET"

bucket="arn:aws:s3:::$MINIO_BUCKET"
cat > /tmp/api-policy.json <<EOF
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:GetObject"],"Resource":["$bucket/downloads/*","$bucket/analyses/*"]},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["$bucket/thumbnails/*"]}
]}
EOF
cat > /tmp/download-policy.json <<EOF
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["$bucket"],"Condition":{"StringLike":{"s3:prefix":["downloads/*"]}}},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["$bucket/downloads/*"]}
]}
EOF
cat > /tmp/report-policy.json <<EOF
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["$bucket"],"Condition":{"StringLike":{"s3:prefix":["analyses/*"]}}},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["$bucket/analyses/*"]}
]}
EOF
cat > /tmp/analysis-policy.json <<EOF
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:GetObject"],"Resource":["$bucket/downloads/*","$bucket/system/analysis-readiness-v1"]}
]}
EOF
cat > /tmp/canary-policy.json <<EOF
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:GetObject"],"Resource":["$bucket/downloads/*","$bucket/analyses/*"]}
]}
EOF

create_role() {
  user="$1"
  secret="$2"
  policy="$3"
  document="$4"
  mc admin user add local "$user" "$secret"
  mc admin policy create local "$policy" "$document"
  mc admin policy attach local "$policy" --user "$user"
}

create_role "$MINIO_API_ACCESS_KEY" "$MINIO_API_SECRET_KEY" video-api /tmp/api-policy.json
create_role "$MINIO_DOWNLOAD_ACCESS_KEY" "$MINIO_DOWNLOAD_SECRET_KEY" video-download /tmp/download-policy.json
create_role "$MINIO_REPORT_ACCESS_KEY" "$MINIO_REPORT_SECRET_KEY" video-report /tmp/report-policy.json
create_role "$MINIO_ANALYSIS_ACCESS_KEY" "$MINIO_ANALYSIS_SECRET_KEY" video-analysis /tmp/analysis-policy.json
create_role "$MINIO_CANARY_ACCESS_KEY" "$MINIO_CANARY_SECRET_KEY" video-canary /tmp/canary-policy.json
printf '%s' 'framefetch-analysis-readiness-v1' | mc pipe "local/$MINIO_BUCKET/system/analysis-readiness-v1" >/dev/null

# Disable the former broad development account when upgrading an existing volume.
mc admin user disable local video-app-access >/dev/null 2>&1 || true
