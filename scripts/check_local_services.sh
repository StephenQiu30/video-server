#!/usr/bin/env bash
set -euo pipefail

if [ ! -f ".env" ]; then
  echo "未找到 .env，已从 .env.example 创建本地开发配置"
  cp .env.example .env
fi

set -a
. ./.env
set +a

PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" - <<'PY'
import os
import shutil
from urllib.parse import urlparse

print("Python 环境 OK")
print(f"FFmpeg: {'OK' if shutil.which('ffmpeg') else '未安装，本地开发可降级；Docker 上线镜像内置'}")
print(f"ffprobe: {'OK' if shutil.which('ffprobe') else '未安装，本地开发可降级；Docker 上线镜像内置'}")

database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://video:video@127.0.0.1:5432/video_downloader")
redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
s3_endpoint = os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")

print(f"PostgreSQL: {database_url}")
print(f"Redis/RQ: {redis_url}")
print(f"MinIO/S3: {s3_endpoint}")
print("请确认以上本地服务已启动；本项目本地开发不强制使用 Docker。")
PY
