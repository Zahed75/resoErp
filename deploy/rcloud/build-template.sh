#!/usr/bin/env bash
# Build the rcloud_template golden database used to provision tenants.
#
# Creates (or recreates, with -f) the rcloud_template database and
# installs the rcloud module set with no demo data.
set -euo pipefail

ODOO_BIN="${ODOO_BIN:-./odoo-bin}"
ODOO_CONF="${ODOO_CONF:-./odoo.conf}"
TEMPLATE_DB="${TEMPLATE_DB:-rcloud_template}"
MODULES="${MODULES:-rcloud_base,rcloud_pms,rcloud_kyc,rcloud_whatsapp,rcloud_tenant_agent}"
FORCE=0

while getopts "f" opt; do
    case "$opt" in
        f) FORCE=1 ;;
        *) echo "Usage: $0 [-f]" >&2; exit 2 ;;
    esac
done

if psql -d postgres -Atc \
        "SELECT 1 FROM pg_database WHERE datname = '$TEMPLATE_DB'" | grep -q 1; then
    if [ "$FORCE" -eq 1 ]; then
        echo "Dropping existing $TEMPLATE_DB ..."
        psql -d postgres -c "DROP DATABASE $TEMPLATE_DB WITH (FORCE)"
    else
        echo "Template $TEMPLATE_DB already exists (use -f to recreate)." >&2
        exit 1
    fi
fi

echo "Creating $TEMPLATE_DB ..."
createdb "$TEMPLATE_DB"

echo "Installing modules: $MODULES ..."
"$ODOO_BIN" -c "$ODOO_CONF" -d "$TEMPLATE_DB" \
    -i "$MODULES" \
    --without-demo=all \
    --stop-after-init

echo "Template $TEMPLATE_DB ready."
