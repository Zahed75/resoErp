#!/usr/bin/env bash
# resoERP backup — database dump + filestore archive, with 14-day retention.
# Run from the project root (next to docker-compose.yml), e.g. via cron:
#   0 3 * * * cd /path/to/resoERP && ./scripts/backup.sh >> /var/log/resoerp_backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DB_NAME="${DB_NAME:-resoSolution}"
DB_USER="${DB_USER:-odoo}"
DB_CONTAINER="${DB_CONTAINER:-resoerp_db}"
FILESTORE_VOLUME="${FILESTORE_VOLUME:-resoerp_filestore}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="$BACKUP_DIR/${DB_NAME}_${STAMP}.dump"
FILES_FILE="$BACKUP_DIR/${DB_NAME}_filestore_${STAMP}.tar.gz"

echo "[$(date)] Backing up database '$DB_NAME'..."
docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$DUMP_FILE"

echo "[$(date)] Archiving filestore volume '$FILESTORE_VOLUME'..."
docker run --rm -v "$FILESTORE_VOLUME":/data:ro -v "$(realpath "$BACKUP_DIR")":/backup alpine \
    tar czf "/backup/$(basename "$FILES_FILE")" -C /data .

echo "[$(date)] Pruning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.dump" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "${DB_NAME}_filestore_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete

echo "[$(date)] Backup complete: $DUMP_FILE + $FILES_FILE"
