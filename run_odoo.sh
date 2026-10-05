#!/bin/bash
# Simple wrapper to run Odoo locally for resoERP

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_NAME="resoSolution"
PORT="8069"
# Current product stack. The legacy reso_pms/reso_ownership modules must NOT
# be auto-installed: they duplicate the "Reso PMS" app and restore the old
# screens (old dashboard, no sidebar, no white theme).
INIT_MODULES="rcloud_base,rcloud_pms,rcloud_pms_account,rcloud_ownership,rcloud_portal_api,rcloud_pos_bridge,rcloud_ui,rcloud_whatsapp,rcloud_tenant_agent,rcloud_control,rcloud_kyc"

cd "$PROJECT_DIR"

if [ -f "$PROJECT_DIR/env/bin/activate" ]; then
    source "$PROJECT_DIR/env/bin/activate"
elif [ -f "/Users/zahed/Downloads/OdooProject/pepperoniHq/env/bin/activate" ]; then
    source /Users/zahed/Downloads/OdooProject/pepperoniHq/env/bin/activate
fi

# First run: create the database with demo data and the full stack so the
# product comes up complete (white theme, sidebar, PMS dashboard) instead
# of a bare Odoo that would need manual module installation.
DB_HOST="$(python3 - "$PROJECT_DIR/odoo.conf" <<'EOF'
import configparser, sys
c = configparser.ConfigParser()
c.read(sys.argv[1])
print(c.get('options', 'db_host', fallback='/tmp'))
EOF
)"
DB_USER="$(python3 - "$PROJECT_DIR/odoo.conf" <<'EOF'
import configparser, sys
c = configparser.ConfigParser()
c.read(sys.argv[1])
print(c.get('options', 'db_user', fallback=''))
EOF
)"
if ! psql -h "$DB_HOST" -U "$DB_USER" -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1; then
    echo "Database '$DB_NAME' not found — initializing with demo data ($INIT_MODULES)..."
    python3 odoo-bin \
        -c odoo.conf \
        -d "$DB_NAME" \
        --db-filter=^${DB_NAME}$ \
        -i "$INIT_MODULES" \
        --with-demo \
        --stop-after-init
fi

python3 odoo-bin \
    -c odoo.conf \
    -d "$DB_NAME" \
    --db-filter=^${DB_NAME}$ \
    --http-interface=127.0.0.1 \
    --http-port="$PORT" \
    --dev=xml \
    --max-cron-threads=0 \
    "$@"
