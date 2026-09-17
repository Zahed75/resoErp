# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFolioAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.property = cls.env['rcloud.property'].create({
            'name': 'Accounting Resort', 'code': 'ACC',
        })
        cls.room_type = cls.env['rcloud.room.type'].create({
            'name': 'Suite', 'property_id': cls.property.id,
            'default_rate': 10000.0,
        })
        cls.room = cls.env['rcloud.room'].create({
            'name': '301', 'property_id': cls.property.id,
            'room_type_id': cls.room_type.id,
        })
        cls.income_account = cls.env['account.account'].create({
            'name': 'Room Revenue (Test)', 'code': 'XR1000',
            'account_type': 'income',
            'company_ids': [(6, 0, cls.company.ids)],
        })
        cls.receivable_account = cls.env['account.account'].create({
            'name': 'Receivables (Test)', 'code': 'XR1300',
            'account_type': 'asset_receivable',
            'company_ids': [(6, 0, cls.company.ids)],
        })
        cls.property.income_account_id = cls.income_account
        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Sales (Test)', 'type': 'sale', 'code': 'TSAJ',
            'company_id': cls.company.id,
        })
        cls.cash_journal = cls.env['account.journal'].create({
            'name': 'Cash (Test)', 'type': 'cash', 'code': 'TCSH',
            'company_id': cls.company.id,
        })
        cls.tax = cls.env['account.tax'].create({
            'name': 'VAT 15%', 'amount': 15.0,
            'amount_type': 'percent', 'type_tax_use': 'sale',
        })
        cls.guest = cls.env['res.partner'].create({
            'name': 'John Guest',
            'property_account_receivable_id': cls.receivable_account.id,
        })
        cls.other_property = cls.env['rcloud.property'].create({
            'name': 'Accounting Resort B', 'code': 'ACB',
        })
        cls.today = fields.Date.today()

    def _checked_in_stay(self):
        today = self.today
        res = self.env['rcloud.reservation'].create({
            'property_id': self.property.id,
            'room_type_id': self.room_type.id,
            'guest_id': self.guest.id,
            'arrival': today,
            'departure': today + timedelta(days=3),
        })
        self.env['rcloud.availability'].sudo().ensure_buckets(
            self.property.id, self.room_type.id, res.arrival, res.departure)
        res.action_confirm()
        res.action_check_in()
        return res

    def test_post_invoice_analytic_and_amounts(self):
        res = self._checked_in_stay()
        folio = res.folio_id
        folio.line_ids = [
            (0, 0, {
                'date': self.today, 'description': 'Room nights',
                'qty': 3, 'unit_price': 10000.0, 'source': 'room',
                'tax_ids': [(6, 0, self.tax.ids)],
            }),
            (0, 0, {
                'date': self.today, 'description': 'Dinner POS',
                'qty': 1, 'unit_price': 2000.0, 'source': 'pos',
            }),
        ]
        move = folio.action_post_invoice()
        self.assertEqual(move.state, 'posted')
        self.assertEqual(move.partner_id, self.guest)
        self.assertEqual(len(move.invoice_line_ids), 2)
        analytic_id = str(self.property.analytic_account_id.id)
        for line in move.invoice_line_ids:
            self.assertIn(analytic_id, line.analytic_distribution or {})
        self.assertEqual(move.amount_untaxed, 32000.0)
        self.assertEqual(move.amount_tax, 4500.0)
        self.assertEqual(move.amount_total, 36500.0)
        # Idempotent: posting again returns the same move.
        self.assertEqual(folio.action_post_invoice(), move)

        # Deposit payment is posted and reconciles the invoice.
        payment = folio.action_apply_deposit(5000.0,
                                             journal=self.cash_journal)
        # Odoo 19: a posted payment is 'in_process' until fully reconciled.
        self.assertEqual(payment.state, 'in_process')
        self.assertEqual(payment.move_id.state, 'posted')
        move.invalidate_recordset()
        self.assertEqual(move.amount_residual, 31500.0)
        self.assertEqual(move.payment_state, 'partial')

    def test_reports_render(self):
        res = self._checked_in_stay()
        folio = res.folio_id
        folio.line_ids = [
            (0, 0, {
                'date': self.today, 'description': 'Room nights',
                'qty': 3, 'unit_price': 10000.0, 'source': 'room',
                'tax_ids': [(6, 0, self.tax.ids)],
            }),
        ]
        move = folio.action_post_invoice()
        Report = self.env['ir.actions.report']
        folio_pdf, _mime = Report._render_qweb_pdf(
            'rcloud_pms_account.action_report_folio', [folio.id])
        self.assertTrue(folio_pdf)
        invoice_pdf, _mime = Report._render_qweb_pdf(
            'rcloud_pms_account.action_report_tax_invoice', [move.id])
        self.assertTrue(invoice_pdf)

    def test_reservation_invoice_stay(self):
        res = self._checked_in_stay()
        res.folio_id.line_ids = [
            (0, 0, {
                'date': self.today, 'description': 'Room nights',
                'qty': 3, 'unit_price': 10000.0, 'source': 'room',
            }),
        ]
        res.action_invoice_stay()
        self.assertEqual(res.state, 'invoiced')
        self.assertTrue(res.folio_id.invoice_ids)

    def test_per_property_pl_reconciles_to_consolidated(self):
        AccountMove = self.env['account.move'].sudo()
        moves = AccountMove
        for prop, amount in ((self.property, 1000.0),
                             (self.other_property, 2500.0)):
            moves |= AccountMove.create({
                'move_type': 'entry',
                'journal_id': self.sale_journal.id,
                'date': self.today,
                'line_ids': [
                    (0, 0, {
                        'name': 'Revenue %s' % prop.code,
                        'account_id': self.income_account.id,
                        'credit': amount,
                        'analytic_distribution': {
                            str(prop.analytic_account_id.id): 100},
                    }),
                    (0, 0, {
                        'name': 'Receivable',
                        'account_id': self.receivable_account.id,
                        'debit': amount,
                    }),
                ],
            })
        moves.action_post()
        MoveLine = self.env['account.move.line'].sudo()
        income_lines = MoveLine.search([
            ('move_id', 'in', moves.ids),
            ('account_id.account_type', '=', 'income'),
        ])
        total = sum(income_lines.mapped('balance'))
        per_property = 0.0
        for prop in (self.property, self.other_property):
            lines = income_lines.filtered(
                lambda l: str(prop.analytic_account_id.id)
                in (l.analytic_distribution or {}))
            per_property += sum(lines.mapped('balance'))
        self.assertAlmostEqual(per_property, total, places=2)
