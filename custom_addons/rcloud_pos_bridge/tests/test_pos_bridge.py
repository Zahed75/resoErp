# -*- coding: utf-8 -*-
from datetime import timedelta

import odoo
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPosBridge(TransactionCase):

    def setUp(self):
        super().setUp()
        self.property = self.env['rcloud.property'].create({
            'name': 'POS Resort', 'code': 'POS'})
        self.rt = self.env['rcloud.room.type'].create({
            'name': 'Std', 'property_id': self.property.id,
            'default_rate': 3000.0})
        self.room = self.env['rcloud.room'].create({
            'name': '101', 'property_id': self.property.id,
            'room_type_id': self.rt.id})
        self.guest = self.env['res.partner'].create({'name': 'Hungry Guest'})
        self.folio = self.env['rcloud.folio'].create({
            'partner_id': self.guest.id})

    def test_pos_charge_posts_to_folio(self):
        lines = self.folio.add_pos_charge([
            {'description': 'Grilled sea bass', 'qty': 2, 'unit_price': 1200},
            {'description': 'Lemonade', 'qty': 2, 'unit_price': 250},
        ], reference='TABLE-7')
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped('source'), ['pos', 'pos'])
        self.assertEqual(self.folio.balance, 2 * 1200 + 2 * 250)

    def test_closed_folio_rejects_pos_charge(self):
        self.folio.action_close()
        with self.assertRaises(UserError):
            self.folio.add_pos_charge(
                [{'description': 'Late snack', 'qty': 1, 'unit_price': 500}])

    def test_empty_charge_rejected(self):
        with self.assertRaises(UserError):
            self.folio.add_pos_charge([])
