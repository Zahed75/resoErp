# -*- coding: utf-8 -*-
from datetime import timedelta

import odoo
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDashboardStats(TransactionCase):

    def setUp(self):
        super().setUp()
        self.property = self.env['rcloud.property'].create({
            'name': 'Dash Resort', 'code': 'DSH'})
        self.rt = self.env['rcloud.room.type'].create({
            'name': 'King', 'property_id': self.property.id, 'default_rate': 4000.0})
        self.room = self.env['rcloud.room'].create({
            'name': '301', 'property_id': self.property.id,
            'room_type_id': self.rt.id})
        self.guest = self.env['res.partner'].create({'name': 'Dash Guest'})
        self.env['rcloud.availability'].sudo().ensure_buckets(
            self.property.id, self.rt.id,
            odoo.fields.Date.today(),
            odoo.fields.Date.today() + timedelta(days=5))
        self.res = self.env['rcloud.reservation'].create({
            'property_id': self.property.id,
            'room_type_id': self.rt.id,
            'guest_id': self.guest.id,
            'arrival': odoo.fields.Date.today(),
            'departure': odoo.fields.Date.today() + timedelta(days=2),
        })

    def test_stats_payload(self):
        self.res.action_confirm()
        stats = self.env['rcloud.reservation'].get_dashboard_stats(
            self.property.id)
        self.assertIn('kpis', stats)
        self.assertEqual(stats['kpis']['rooms_total'], 1)
        self.assertIn('revenue_by_source', stats)
        self.assertTrue(
            any(s['source'] == 'direct' for s in stats['revenue_by_source']))

    def test_daily_stat_compute_and_uniq(self):
        Daily = self.env['rcloud.pms.daily.stat'].sudo()
        Daily._compute_for_date(self.property, odoo.fields.Date.today())
        stat = Daily.search([('property_id', '=', self.property.id),
                             ('date', '=', odoo.fields.Date.today())])
        self.assertEqual(len(stat), 1)
        # Idempotent recompute, no duplicate
        Daily._compute_for_date(self.property, odoo.fields.Date.today())
        self.assertEqual(Daily.search_count([
            ('property_id', '=', self.property.id),
            ('date', '=', odoo.fields.Date.today())]), 1)

    def test_stats_respect_property_filter(self):
        other = self.env['rcloud.property'].create({
            'name': 'Other Dash', 'code': 'DSH2'})
        stats = self.env['rcloud.reservation'].get_dashboard_stats(other.id)
        self.assertEqual(stats['kpis']['rooms_total'], 0)
