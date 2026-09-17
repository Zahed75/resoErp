#!/usr/bin/env bash
# Nightly per-tenant backup: pg_dump every tenant database + filestore
# tarball, kept for 30 days.
#
# Usage: backup-tenants.sh [backup_root] [data_dir]
#   backup_root  defaults to ./backups
#   data_dir     Odoo data dir containing filestore/, defaults to
#                ~/.local/share/Odoo
set -euo pipefail

BACKUP_ROOT="${1:-./backups}"
DATA_DIR="${2:-$HOME/.local/share/Odoo}"
FILESTORE_DIR="$DATA_DIR/filestore"
RETENTION_DAYS=30
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

export PGHOST="${PGHOST:-/tmp}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-$USER}"

mkdir -p "$BACKUP_ROOT"

# Tenant databases are everything named rcloud_* except template.
mapfile -t DBS < <(psql -d postgres -Atc \
    "SELECT datname FROM pg_database WHERE datname LIKE 'rcloud\_%' AND datname <> 'rcloud_template'")

if [ "${#DBS[@]}" -eq 0 ]; then
    echo "No tenant databases found." >&2
fi

for db in "${DBS[@]}"; do
    out_dir="$BACKUP_ROOT/$db"
    mkdir -p "$out_dir"

    echo "Dumping $db ..."
    pg_dump -Fc "$db" > "$out_dir/${db}_${TIMESTAMP}.dump"

    if [ -d "$FILESTORE_DIR/$db" ]; then
        echo "Archiving filestore for $db ..."
        tar -C "$FILESTORE_DIR" -czf \
            "$out_dir/${db}_${TIMESTAMP}_filestore.tar.gz" "$db"
    fi
done

# Prune dumps older than the retention window.
find "$BACKUP_ROOT" -type f \( -name '*.dump' -o -name '*_filestore.tar.gz' \) \
    -mtime "+$RETENTION_DAYS" -print -delete

echo "Backup complete: ${#DBS[@]} tenant(s) -> $BACKUP_ROOT"
