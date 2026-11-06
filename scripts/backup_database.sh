#!/usr/bin/env bash
# =============================================================================
# PropVal AI — Automated Database Backup Script (PostgreSQL + PostGIS)
# Usage:
#   ./scripts/backup_database.sh [backup_dir]
# Cron schedule recommendation: 0 2 * * * (Daily at 02:00 UTC)
# =============================================================================
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/propval_db_${TIMESTAMP}.sql.gz"
METADATA_FILE="${BACKUP_DIR}/propval_db_${TIMESTAMP}.meta.json"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] [$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting PropVal AI database backup..."

if [ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL}" == postgresql* ]]; then
    # PostgreSQL / PostGIS Dump via pg_dump
    echo "[INFO] Connecting to PostgreSQL database..."
    pg_dump "${DATABASE_URL}" --format=plain --no-owner --no-privileges | gzip > "${BACKUP_FILE}"
elif [ -f "./propval.db" ]; then
    # SQLite fallback dump for isolated environments
    echo "[INFO] Backing up local SQLite database file..."
    sqlite3 ./propval.db ".backup '${BACKUP_DIR}/propval_db_${TIMESTAMP}.sqlite'"
    gzip -f "${BACKUP_DIR}/propval_db_${TIMESTAMP}.sqlite"
    BACKUP_FILE="${BACKUP_DIR}/propval_db_${TIMESTAMP}.sqlite.gz"
else
    echo "[ERROR] No valid database detected for backup." >&2
    exit 1
fi

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
FILE_SHA256=$(sha256sum "${BACKUP_FILE}" | cut -d' ' -f1)

cat <<EOF > "${METADATA_FILE}"
{
  "timestamp": "${TIMESTAMP}",
  "file": "${BACKUP_FILE}",
  "sha256": "${FILE_SHA256}",
  "size": "${FILE_SIZE}",
  "backup_status": "SUCCESS"
}
EOF

echo "[INFO] Database backup completed successfully: ${BACKUP_FILE} (Size: ${FILE_SIZE}, SHA256: ${FILE_SHA256})"

# Retention policy: Delete backups older than 30 days
find "${BACKUP_DIR}" -type f -name "propval_db_*" -mtime +30 -delete
echo "[INFO] Retention cleanup complete (30-day policy enforced)."

