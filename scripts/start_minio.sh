#!/usr/bin/env bash
# Start MinIO locally on macOS using Homebrew

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINIO_DATA_DIR="${ROOT_DIR}/tmp/minio-data"
mkdir -p "${MINIO_DATA_DIR}"

if ! command -v minio &> /dev/null; then
  echo "=========================================================="
  echo "❌ MinIO 未在当前系统安装！"
  echo "您可以使用 Homebrew 快速安装："
  echo "  brew install minio/stable/minio"
  echo "=========================================================="
  exit 1
fi

echo "=========================================================="
echo "🚀 正在启动本地宿主机 MinIO 服务..."
echo "📂 数据存储目录: ${MINIO_DATA_DIR}"
echo "🌐 API 服务地址: http://127.0.0.1:9000"
echo "🖥️ 控制台管理页: http://127.0.0.1:9001"
echo "=========================================================="

export MINIO_ROOT_USER=minio
export MINIO_ROOT_PASSWORD=stephenqhd30.

exec minio server "${MINIO_DATA_DIR}" --address "127.0.0.1:9000" --console-address "127.0.0.1:9001"
