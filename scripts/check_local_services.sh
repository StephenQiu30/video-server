#!/usr/bin/env bash
# check_local_services.sh — 本机依赖服务连通性探测
# 实际尝试连接 Postgres、Redis、MinIO，报告状态并在缺失时给出修复建议。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "${ROOT_DIR}/.env" ]; then
  echo "未找到 .env，已从 .env.example 创建本地开发配置"
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
fi

# 仅从 .env 加载尚未在环境中设置的变量（环境变量优先）
while IFS='=' read -r key value; do
  key="$(echo "${key}" | xargs)"
  [[ -z "${key}" || "${key}" == \#* ]] && continue
  value="$(echo "${value}" | xargs | sed 's/^"//;s/"$//')"
  if [ -z "${!key+x}" ]; then
    export "${key}=${value}"
  fi
done < "${ROOT_DIR}/.env"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "FAIL: Python 未找到 (${PYTHON_BIN})"
  echo "  提示: brew install python3 或创建 .venv 后设置 PYTHON_BIN"
  exit 1
fi

echo "Python 环境 OK"
echo "FFmpeg: $('${PYTHON_BIN}' -c 'import shutil; print("OK" if shutil.which("ffmpeg") else "未安装 (可选, Docker 镜像内置)")' 2>/dev/null || echo '未安装 (可选)')"
echo "ffprobe: $('${PYTHON_BIN}' -c 'import shutil; print("OK" if shutil.which("ffprobe") else "未安装 (可选, Docker 镜像内置)")' 2>/dev/null || echo '未安装 (可选)')"
echo ""

EXIT_CODE=0

"${PYTHON_BIN}" - <<'PY' || EXIT_CODE=$?
import os
import socket
import sys
from urllib.parse import urlparse

results = []

# --- PostgreSQL ---
db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://video:video@127.0.0.1:5432/video_downloader")
parsed = urlparse(db_url)
db_host = parsed.hostname or "127.0.0.1"
db_port = parsed.port or 5432
db_ok = False
db_msg = ""

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    sock.connect((db_host, db_port))
    sock.close()
    db_ok = True
    db_msg = "OK"
except (socket.timeout, ConnectionRefusedError, OSError) as exc:
    db_msg = f"不可达 ({exc})"
finally:
    try:
        sock.close()
    except Exception:
        pass

status = "OK" if db_ok else "FAIL"
print(f"PostgreSQL [{status}]: {db_url}")
if not db_ok:
    print(f"  提示: 确认 Postgres 已启动并监听 {db_host}:{db_port}")
    print(f"        Docker: docker run -d -p 5432:5432 -e POSTGRES_USER=video -e POSTGRES_PASSWORD=video -e POSTGRES_DB=video_downloader postgres:16")
    print(f"        macOS:  brew services start postgresql@16")
    print(f"        Linux:  sudo systemctl start postgresql")
results.append(db_ok)

# --- Redis ---
redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
rparsed = urlparse(redis_url)
redis_host = rparsed.hostname or "127.0.0.1"
redis_port = rparsed.port or 6379
redis_ok = False
redis_msg = ""

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    sock.connect((redis_host, redis_port))
    sock.sendall(b"PING\r\n")
    resp = sock.recv(64)
    sock.close()
    if b"PONG" in resp:
        redis_ok = True
        redis_msg = "OK (PONG)"
    else:
        redis_msg = f"连接成功但 PING 未返回 PONG: {resp!r}"
except (socket.timeout, ConnectionRefusedError, OSError) as exc:
    redis_msg = f"不可达 ({exc})"
finally:
    try:
        sock.close()
    except Exception:
        pass

status = "OK" if redis_ok else "FAIL"
print(f"Redis/RQ    [{status}]: {redis_url}")
if not redis_ok:
    print(f"  提示: 确认 Redis 已启动并监听 {redis_host}:{redis_port}")
    print(f"        Docker: docker run -d -p 6379:6379 redis:7")
    print(f"        macOS:  brew services start redis")
    print(f"        Linux:  sudo systemctl start redis")
results.append(redis_ok)

# --- MinIO / S3 ---
s3_endpoint = os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
s3_parsed = urlparse(s3_endpoint)
s3_host = s3_parsed.hostname or "127.0.0.1"
s3_port = s3_parsed.port or (443 if s3_parsed.scheme == "https" else 9000)
s3_ok = False
s3_msg = ""

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    sock.connect((s3_host, s3_port))
    sock.close()
    s3_ok = True
    s3_msg = "OK"
except (socket.timeout, ConnectionRefusedError, OSError) as exc:
    s3_msg = f"不可达 ({exc})"
finally:
    try:
        sock.close()
    except Exception:
        pass

status = "OK" if s3_ok else "FAIL"
print(f"MinIO/S3    [{status}]: {s3_endpoint}")
if not s3_ok:
    print(f"  提示: 确认 MinIO 已启动并监听 {s3_host}:{s3_port}")
    print(f"        Docker: docker run -d -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ':9001'")
    print(f"        macOS:  brew install minio/stable/minio && minio server /tmp/minio-data")
results.append(s3_ok)

# --- Summary ---
all_ok = all(results)
print()
if all_ok:
    print("所有依赖服务连接正常，可以启动本机开发环境。")
else:
    fail_count = results.count(False)
    print(f"有 {fail_count} 个服务不可达，请先启动缺失的服务再运行 npm start。")

sys.exit(0 if all_ok else 1)
PY

exit "${EXIT_CODE}"
