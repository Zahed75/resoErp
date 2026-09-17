# -*- coding: utf-8 -*-
from datetime import timedelta

import odoo
from odoo import api
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestReservation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import os
        code = 'R%d' % (os.getpid() % 100000)
        cr = odoo.sql_db.db_connect(cls.env.cr.dbname).cursor()
        env = api.Environment(cr, cls.env.uid, {})
        cls.property = env['rcloud.property'].create({
            'name': 'Lifecycle Resort %s' % code, 'code': code,
        })
        cls.room_type = env['rcloud.room.type'].create({
            'name': 'Suite', 'property_id': cls.property.id,
            'default_rate': 8000.0,
        })
        cls.room = env['rcloud.room'].create({
            'name': '201', 'property_id': cls.property.id,
            'room_type_id': cls.room_type.id,
        })
        cls.guest = env['res.partner'].create({'name': 'Jane Doe'})
        prop_id, rt_id, room_id, guest_id = (
            cls.property.id, cls.room_type.id, cls.room.id, cls.guest.id)
        cr.commit()
        cr.close()
        # Re-browse through the class environment: records created with the
        # fixture cursor would otherwise keep reading from that closed cursor.
        cls.property = cls.env['rcloud.property'].browse(prop_id)
        cls.room_type = cls.env['rcloud.room.type'].browse(rt_id)
        cls.room = cls.env['rcloud.room'].browse(room_id)
        cls.guest = cls.env['res.partner'].browse(guest_id)
        cls.today = odoo.fields.Date.today()

    def _create(self, **kw):
        vals = {
            'property_id': self.property.id,
            'room_type_id': self.room_type.id,
            'guest_id': self.guest.id,
            'arrival': self.today + timedelta(days=60),
            'departure': self.today + timedelta(days=63),
        }
        vals.update(kw)
        res = self.env['rcloud.reservation'].create(vals)
        # Open inventory for the stay (normally the night-audit cron's job).
        self.env['rcloud.availability'].sudo().ensure_buckets(
            vals['property_id'], vals['room_type_id'],
            vals['arrival'], vals['departure'])
        return res

    def test_full_lifecycle(self):
        res = self._create()
        self.assertEqual(res.state, 'draft')
        res.action_confirm()
        self.assertEqual(res.state, 'confirmed')
        self.assertEqual(len(res.line_ids), 3)
        self.assertEqual(res.amount_total, 3 * 8000.0)

        res.action_check_in()
        self.assertEqual(res.state, 'checked_in')
        self.assertEqual(res.room_id, self.room)
        self.assertEqual(self.room.status, 'occupied')
        self.assertTrue(res.folio_id)

        res.action_check_out()
        self.assertEqual(res.state, 'checked_out')
        self.assertEqual(self.room.status, 'vacant_dirty')
        self.assertEqual(res.folio_id.state, 'closed')

    def test_invalid_transitions_blocked(self):
        res = self._create()
        with self.assertRaises(UserError):
            res.action_check_in()
        with self.assertRaises(UserError):
            res.action_check_out()
        res.action_hold()
        with self.assertRaises(UserError):
            res.action_hold()
        res.action_cancel()
        self.assertEqual(res.state, 'cancelled')
        with self.assertRaises(UserError):
            res.action_confirm()

    def test_cancel_releases_inventory(self):
        d1 = self.today + timedelta(days=70)
        res = self._create(arrival=d1, departure=d1 + timedelta(days=1))
        res.action_confirm()
        buckets = self.env['rcloud.availability'].sudo().search_buckets(
            self.property.id, self.room_type.id, d1, d1 + timedelta(days=1))
        self.assertEqual(buckets.sold, 1)
        res.action_cancel()
        buckets.invalidate_recordset()
        self.assertEqual(buckets.sold, 0)

    def test_rate_calendar_pricing_and_min_stay(self):
        plan = self.env['rcloud.rate.plan'].create({
            'name': 'Winter Promo', 'property_id': self.property.id,
            'room_type_id': self.room_type.id,
        })
        d1 = self.today + timedelta(days=80)
        self.env['rcloud.rate.calendar'].create({
            'rate_plan_id': plan.id, 'date': d1,
            'rate': 6500.0, 'min_stay': 2,
        })
        res = self._create(arrival=d1, departure=d1 + timedelta(days=1),
                           rate_plan_id=plan.id)
        with self.assertRaises(UserError):
            res.action_confirm()  # 1 night < min_stay 2

        res.departure = d1 + timedelta(days=2)
        # Stay extended: open inventory for the extra night first.
        self.env['rcloud.availability'].sudo().ensure_buckets(
            self.property.id, self.room_type.id, d1, d1 + timedelta(days=2))
        res.action_confirm()
        rates = res.line_ids.sorted('date').mapped('rate')
        self.assertEqual(rates[0], 6500.0)
        self.assertEqual(rates[1], 8000.0)  # fallback to default rate

    def test_property_mismatch_rejected(self):
        other_prop = self.env['rcloud.property'].create({
            'name': 'Other', 'code': 'OTR',
        })
        with self.assertRaises(Exception):
            self._create(property_id=other_prop.id)
