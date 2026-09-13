#!/bin/bash
# Simple wrapper to run Odoo locally for resoERP

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_NAME="resoSolution"
PORT="8069"

cd "$PROJECT_DIR"

if [ -f "$PROJECT_DIR/env/bin/activate" ]; then
    source "$PROJECT_DIR/env/bin/activate"
elif [ -f "/Users/zahed/Downloads/OdooProject/pepperoniHq/env/bin/activate" ]; then
    source /Users/zahed/Downloads/OdooProject/pepperoniHq/env/bin/activate
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
