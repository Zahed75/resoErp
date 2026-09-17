# -*- coding: utf-8 -*-
import psycopg2
from psycopg2 import sql as psql

from odoo import models


def admin_cursor():
    """Autocommit connection to the 'postgres' maintenance database for
    database-level DDL (CREATE/DROP DATABASE). Never use inside a
    transaction: those statements cannot run in one."""
    connection = psycopg2.connect(**_admin_connection_params())
    connection.autocommit = True
    return connection.cursor()


def _admin_connection_params():
    from odoo.sql_db import connection_info_for
    _db, info = connection_info_for('postgres')
    info = dict(info)
    info.pop('database', None)
    info['dbname'] = 'postgres'
    return info


def database_exists(cr, db_name):
    cr.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    return cr.fetchone() is not None


def create_database(db_name, template=None):
    """Idempotent CREATE DATABASE on an autocommit admin connection."""
    with admin_cursor() as cr:
        if database_exists(cr, db_name):
            return False
        query = psql.SQL("CREATE DATABASE {}").format(
            psql.Identifier(db_name))
        if template:
            query = psql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                psql.Identifier(db_name), psql.Identifier(template))
        cr.execute(query)
        return True


def drop_database(db_name):
    """Idempotent DROP DATABASE ... WITH (FORCE) on an autocommit admin
    connection; refuses to drop the control-plane database itself."""
    from odoo.tools import config
    db_names = config.get('db_name') or []
    if isinstance(db_names, str):
        db_names = db_names.split(',')
    forbidden = set(db_names) | {'postgres', 'template0', 'template1'}
    if db_name in forbidden:
        return False
    with admin_cursor() as cr:
        if not database_exists(cr, db_name):
            return False
        cr.execute(psql.SQL("DROP DATABASE {} WITH (FORCE)").format(
            psql.Identifier(db_name)))
        return True


def exec_retry(cr, query, params=None, retries=3):
    """Run raw SQL inside a savepoint, retrying serialization failures
    (all connections run REPEATABLE READ). Returns fetched rows for
    SELECT statements, None otherwise."""
    for attempt in range(retries):
        cr.execute('SAVEPOINT rcloud_exec')
        try:
            cr.execute(query, params or ())
            rows = cr.fetchall() if cr.description is not None else None
            cr.execute('RELEASE SAVEPOINT rcloud_exec')
            return rows
        except psycopg2.errors.SerializationFailure:
            cr.execute('ROLLBACK TO SAVEPOINT rcloud_exec')
            cr.execute('RELEASE SAVEPOINT rcloud_exec')
            if attempt == retries - 1:
                raise
