#!/usr/bin/env bash
# Provision a new tenant database from the rcloud_template golden image.
#
# Usage: provision-tenant.sh <subdomain> [db_name]
#   subdomain  e.g. acme  -> acme.resocloud.example.com
#   db_name    defaults to rcloud_<subdomain>
#
# Creates the database (TEMPLATE rcloud_template) and copies the template
# filestore, then prints the control-plane registration steps.
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <subdomain> [db_name]" >&2
    exit 2
fi

SUBDOMAIN="$1"
DB_NAME="${2:-rcloud_$SUBDOMAIN}"
TEMPLATE_DB="${TEMPLATE_DB:-rcloud_template}"
DATA_DIR="${DATA_DIR:-$HOME/.local/share/Odoo}"

case "$SUBDOMAIN" in
    www|admin|api|app|mail|static|web|billing|status|support|blog|docs)
        echo "Subdomain '$SUBDOMAIN' is reserved." >&2; exit 1 ;;
esac
if ! [[ "$SUBDOMAIN" =~ ^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$ ]]; then
    echo "Invalid subdomain '$SUBDOMAIN'." >&2; exit 1
fi

if psql -d postgres -Atc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1; then
    echo "Database $DB_NAME already exists." >&2; exit 1
fi

echo "Creating database $DB_NAME from template $TEMPLATE_DB ..."
psql -d postgres -c "CREATE DATABASE $DB_NAME TEMPLATE $TEMPLATE_DB"

if [ -d "$DATA_DIR/filestore/$TEMPLATE_DB" ]; then
    echo "Copying filestore ..."
    cp -a "$DATA_DIR/filestore/$TEMPLATE_DB" "$DATA_DIR/filestore/$DB_NAME"
else
    echo "WARNING: no template filestore at $DATA_DIR/filestore/$TEMPLATE_DB" >&2
fi

cat <<EOF

Tenant '$SUBDOMAIN' provisioned:
  URL:      https://$SUBDOMAIN.resocloud.example.com
  Database: $DB_NAME

Next steps on the control plane:
  1. Create the rcloud.tenant record (subdomain=$SUBDOMAIN, db_name=$DB_NAME, plan).
  2. Run the provision job (or use this script as the copy_template/copy_filestore
     steps) to sign and push the entitlement blob.
  3. Seed tenant admin user + set ir.config_parameter rcloud.tenant_id /
     rcloud.control_plane_url, then verify the billing page.
EOF
