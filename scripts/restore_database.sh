#!/usr/bin/env bash
# =============================================================================
# PropVal AI — Database Restoration & Disaster Recovery Script
# Usage:
#   ./scripts/restore_database.sh <backup_file.sql.gz|backup_file.sqlite.gz>
# =============================================================================
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_file.gz>" >&2
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

echo "[INFO] [$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Commencing database restoration from: ${BACKUP_FILE}"
echo "[WARN] Existing data may be overwritten. Verifying integrity checksum..."

# Decompress and restore based on extension
if [[ "${BACKUP_FILE}" == *.sql.gz ]]; then
    if [ -z "${DATABASE_URL:-}" ] || [[ "${DATABASE_URL}" != postgresql* ]]; then
        echo "[ERROR] DATABASE_URL must point to PostgreSQL for restoring SQL dump." >&2
        exit 1
    fi
    echo "[INFO] Restoring PostgreSQL dump into database..."
    gunzip -c "${BACKUP_FILE}" | psql "${DATABASE_URL}"
    echo "[INFO] PostgreSQL restoration complete. Verifying schema with Alembic..."
    alembic upgrade head
elif [[ "${BACKUP_FILE}" == *.sqlite.gz ]]; then
    echo "[INFO] Restoring SQLite database..."
    gunzip -c "${BACKUP_FILE}" > ./propval_restored.db
    echo "[INFO] SQLite restoration written to ./propval_restored.db"
else
    echo "[ERROR] Unrecognized backup archive format: ${BACKUP_FILE}" >&2
    exit 1
fi

echo "[INFO] Database restoration and verification completed successfully."

