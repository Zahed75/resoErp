#!/bin/bash
set -e

: "${HOST:=db}"
: "${PORT:=5432}"
: "${USER:=odoo}"
: "${PASSWORD:=odoo}"
: "${DB_NAME:=resoSolution}"
: "${ODOO_ADMIN_PASSWD:=admin}"
: "${DEMO:=true}"

# Apply the admin master password from the environment into the runtime config
# (the baked-in conf value is only a fallback for local builds).
sed -i "s|^admin_passwd = .*|admin_passwd = ${ODOO_ADMIN_PASSWD}|" /etc/odoo/odoo.conf

# Demo data (demo/demo_data.xml in both custom addons) loads on module install
# unless DEMO=false.
DEMO_ARGS=()
if [ "$DEMO" = "false" ]; then
    DEMO_ARGS+=(--without-demo=all)
fi

# Wait for PostgreSQL to become available before starting Odoo.
wait_for_postgres() {
    echo "Waiting for PostgreSQL at ${HOST}:${PORT}..."
    local tries=0
    until pg_isready -h "$HOST" -p "$PORT" -U "$USER" -q || [ "$tries" -ge 60 ]; do
        tries=$((tries + 1))
        sleep 1
    done
    if [ "$tries" -ge 60 ]; then
        echo "PostgreSQL did not become ready in time." >&2
        exit 1
    fi
    echo "PostgreSQL is ready."
}

wait_for_postgres

case "$1" in
    odoo)
        shift
        EXTRA_ARGS=()
        if [ -n "$INIT_MODULES" ]; then
            EXTRA_ARGS+=(-i "$INIT_MODULES")
        fi
        if [ -n "$UPDATE_MODULES" ]; then
            EXTRA_ARGS+=(-u "$UPDATE_MODULES")
        fi
        exec /opt/resoerp/odoo-bin \
            -c /etc/odoo/odoo.conf \
            --db_host="$HOST" \
            --db_port="$PORT" \
            --db_user="$USER" \
            --db_password="$PASSWORD" \
            -d "$DB_NAME" \
            "${EXTRA_ARGS[@]}" \
            "${DEMO_ARGS[@]}" \
            "$@"
        ;;
    shell|scaffold|cloc|deploy|populate)
        exec /opt/resoerp/odoo-bin "$@" \
            -c /etc/odoo/odoo.conf \
            --db_host="$HOST" \
            --db_port="$PORT" \
            --db_user="$USER" \
            --db_password="$PASSWORD"
        ;;
    *)
        exec "$@"
        ;;
esac
