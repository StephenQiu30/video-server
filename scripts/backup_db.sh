#!/usr/bin/env bash
# scripts/backup_db.sh
# Simple PostgreSQL backup script for Docker Compose deployment.

set -euo pipefail

# Use environment variables or defaults
BACKUP_DIR="${BACKUP_DIR:-./tmp/backups}"
DB_CONTAINER="${DB_CONTAINER:-video-db}"
DB_USER="${DB_USER:-video}"
DB_NAME="${DB_NAME:-video_downloader}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

echo "Creating backup for database $DB_NAME from container $DB_CONTAINER..."

docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

echo "Backup created at $BACKUP_FILE"

# Retention: keep last 7 days
find "$BACKUP_DIR" -name "db_backup_*.sql" -mtime +7 -delete
echo "Old backups cleaned up."
