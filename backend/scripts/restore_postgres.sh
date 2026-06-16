#!/usr/bin/env bash
# ==============================================================================
# Database Restore Script for production-grade PostgreSQL container
# ==============================================================================
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/backup_file.sql.gz" >&2
    exit 1
fi

BACKUP_FILE="$1"
DB_CONTAINER_NAME="eyewear_postgres"
DB_NAME="${POSTGRES_DB:-eyewear_oms}"
DB_USER="${POSTGRES_USER:-postgres}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

echo "[$(date)] Restoring database from: ${BACKUP_FILE}..."

# 1. Drop existing database connections and recreate the database to ensure clean state
echo "[INFO] Re-creating database ${DB_NAME} to ensure clean restore..."
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "REVOKE CONNECT ON DATABASE ${DB_NAME} FROM public;" || true
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();" || true
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

# 2. Decompress and stream the backup dump into PostgreSQL container
echo "[INFO] Importing SQL data..."
gzip -d -c "${BACKUP_FILE}" | docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" > /dev/null

echo "[$(date)] Database restore completed successfully."
