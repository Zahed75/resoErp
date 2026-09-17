# -*- coding: utf-8 -*-
import multiprocessing
from datetime import timedelta
import itertools
import os

import odoo
from odoo import api
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

_fixture_counter = itertools.count(1)


def _booking_worker(dbname, uid, prop_id, rt_id, d1, d2, queue, i):
    """Attempt to book+confirm the last room from a forked process.

    A fresh process is used instead of threads: Odoo 19's global registry
    lock does not survive multi-threaded Environment creation, while each
    forked process gets a consistent single-threaded copy. Every connection
    in Odoo 19 runs under REPEATABLE READ, so a serialization failure is
    retried in a brand-new transaction (fresh snapshot) before giving up.
    """
    import os
    import threading

    from psycopg2.errors import SerializationFailure
    from odoo.orm.registry import Registry

    # Detach from the connection pool inherited over fork: close only this
    # process's fd copies (the parent's descriptors stay open), then drop the
    # pool entries so fresh connections are created below.
    pool = odoo.sql_db._Pool
    if pool is not None:
        for cnx in list(pool._connections):
            try:
                os.close(cnx.fileno())
            except OSError:
                pass
        pool._connections.clear()
    # The fork may copy the class lock in a contended state — reset it.
    Registry._lock = threading.RLock()

    ok = False
    for _attempt in range(3):
        cr = odoo.sql_db.db_connect(dbname).cursor()
        try:
            env = api.Environment(cr, uid, {})
            res = env['rcloud.reservation'].sudo().create({
                'property_id': prop_id,
                'room_type_id': rt_id,
                'guest_id': env['res.partner'].sudo().create(
                    {'name': 'Race guest %d' % i}).id,
                'arrival': d1,
                'departure': d2,
            })
            res.action_confirm()
            cr.commit()
            ok = True
            break
        except SerializationFailure:
            cr.rollback()  # retry with a fresh snapshot
        except Exception:
            cr.rollback()
            break
        finally:
            cr.close()
    queue.put((i, ok))


def _committed_fixtures(dbname, uid, code=None):
    """Create property/type/room through a committed connection so that
    worker processes (separate connections) can see them. The code is
    unique per run so repeated test runs on the same DB don't collide."""
    code = code or 'C%d_%d' % (os.getpid(), next(_fixture_counter))
    if '_' not in code:
        code = '%s_%d' % (code, next(_fixture_counter))
    cr = odoo.sql_db.db_connect(dbname).cursor()
    env = api.Environment(cr, uid, {})
    prop = env['rcloud.property'].create(
        {'name': 'Cloud Resort %s' % code, 'code': code})
    rt = env['rcloud.room.type'].create({
        'name': 'Deluxe', 'property_id': prop.id, 'default_rate': 5000.0,
    })
    env['rcloud.room'].create({
        'name': '101', 'property_id': prop.id, 'room_type_id': rt.id,
    })
    ids = (prop.id, rt.id)
    cr.commit()
    cr.close()
    return ids


@tagged('post_install', '-at_install')
class TestAvailability(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.property_id, cls.room_type_id = _committed_fixtures(
            cls.env.cr.dbname, cls.env.uid)
        cls.Availability = cls.env['rcloud.availability'].sudo()

    def test_buckets_created_and_allocated(self):
        d1 = odoo.fields.Date.today() + timedelta(days=10)
        d2 = d1 + timedelta(days=2)
        buckets = self.Availability.buckets_for(
            self.property_id, self.room_type_id, d1, d2)
        self.assertEqual(len(buckets), 2)
        self.assertEqual(set(buckets.mapped('total')), {1})

        buckets[0].allocate(1)
        buckets[0].invalidate_recordset()
        self.assertEqual(buckets[0].sold, 1)
        with self.assertRaises(UserError):
            buckets[0].allocate(1)

        buckets[0].release(1)
        buckets[0].invalidate_recordset()
        self.assertEqual(buckets[0].sold, 0)

    def test_ooo_room_blocks_bucket(self):
        d1 = odoo.fields.Date.today() + timedelta(days=20)
        room = self.env['rcloud.room'].search([
            ('room_type_id', '=', self.room_type_id)], limit=1)
        room.write({'is_ooo': True})
        buckets = self.Availability.buckets_for(
            self.property_id, self.room_type_id, d1, d1 + timedelta(days=1))
        self.assertEqual(buckets.blocked, 1)
        room.write({'is_ooo': False})
        buckets.invalidate_recordset()
        self.assertEqual(buckets.blocked, 0)


@tagged('post_install', '-at_install')
class TestAvailabilityConcurrency(TransactionCase):
    """Isolated in its own class: committed worker transactions would
    otherwise poison the REPEATABLE READ snapshot of unrelated tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.property_id, cls.room_type_id = _committed_fixtures(
            cls.env.cr.dbname, cls.env.uid)

    def test_concurrent_last_room_exactly_one_wins(self):
        """MANDATORY (Part 12): 50 simultaneous bookings on the last room
        must result in exactly one success."""
        d1 = odoo.fields.Date.today() + timedelta(days=40)
        d2 = d1 + timedelta(days=1)
        # Pre-create the bucket in a committed transaction so workers only
        # contend on the row lock, not on INSERT-vs-INSERT conflicts.
        cr = odoo.sql_db.db_connect(self.env.cr.dbname).cursor()
        env = api.Environment(cr, self.env.uid, {})
        env['rcloud.availability'].sudo().buckets_for(
            self.property_id, self.room_type_id, d1, d2)
        cr.commit()
        cr.close()

        ctx = multiprocessing.get_context('fork')
        queue = ctx.Queue()
        procs = [ctx.Process(
            target=_booking_worker,
            args=(self.env.cr.dbname, self.env.uid,
                  self.property_id, self.room_type_id, d1, d2, queue, i),
        ) for i in range(50)]
        for p in procs:
            p.start()
        results = {}
        import time as _time
        deadline = _time.time() + 300
        while len(results) < 50 and _time.time() < deadline:
            try:
                i, ok = queue.get(timeout=10)
                results[i] = ok
            except Exception:
                break
        for p in procs:
            p.join(30)
            if p.is_alive():
                p.terminate()
        self.assertEqual(len(results), 50, "All workers must report a result")
        self.assertEqual(sum(1 for ok in results.values() if ok), 1,
                         "Exactly one concurrent booking must succeed")
        # Read-only assertion: plain SELECTs never conflict under RR.
        buckets = self.env['rcloud.availability'].sudo().search_buckets(
            self.property_id, self.room_type_id, d1, d2)
        self.assertEqual(buckets.sold, 1)
