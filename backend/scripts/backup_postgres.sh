#!/usr/bin/env bash
# ==============================================================================
# Database Backup Script for production-grade PostgreSQL container
# ==============================================================================
set -euo pipefail

# Configurations
BACKUP_DIR="${BACKUP_DIR:-/workspace/backups}"
RETENTION_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_CONTAINER_NAME="eyewear_postgres"
DB_NAME="${POSTGRES_DB:-eyewear_oms}"
DB_USER="${POSTGRES_USER:-postgres}"
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting PostgreSQL Backup..."
mkdir -p "${BACKUP_DIR}"

# 1. Generate compressed SQL dump from Docker container
if ! docker exec "${DB_CONTAINER_NAME}" pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
    echo "[ERROR] Backup failed: pg_dump execution failed or container is not running." >&2
    exit 1
fi

echo "[INFO] Database backup written locally to: ${BACKUP_FILE}"

# 2. Upload to S3 if AWS credentials are set
if [ "${AWS_ACCESS_KEY_ID:-}" != "" ] && [ "${AWS_SECRET_ACCESS_KEY:-}" != "" ] && [ "${AWS_S3_BUCKET:-}" != "" ]; then
    echo "[INFO] Uploading backup to S3 bucket ${AWS_S3_BUCKET}..."
    if command -v aws &> /dev/null; then
        aws s3 cp "${BACKUP_FILE}" "s3://${AWS_S3_BUCKET}/db_backups/$(basename "${BACKUP_FILE}")"
        echo "[INFO] Backup uploaded to S3 successfully."
    else
        echo "[WARNING] aws-cli not found, skipping S3 upload."
    fi
fi

# 3. Apply retention policy (clean up old files locally)
echo "[INFO] Applying retention policy: keeping last ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] PostgreSQL Backup finished successfully."
