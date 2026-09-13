from unittest.mock import patch

import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('-at_install', 'post_install')  # Only runs after installation, not at install time
class TestPOSCustomerAccountReconciliation(TestPoSCommon):

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.order_data = [{
            "pos_order_lines_ui_args": [(self.product_a, 1)],
            "payments": [(self.pay_later_pm, 1150)],
            "customer": self.partner_a,
            "is_invoiced": True,
        }, {
            "pos_order_lines_ui_args": [(self.product_a, 1)],
            "payments": [(self.pay_later_pm, 1150)],
            "customer": self.partner_a,
            "is_invoiced": False,
        }, {
            "pos_order_lines_ui_args": [(self.product_a, 1)],
            "payments": [(self.pay_later_pm, 1150)],
            "customer": self.partner_a,
            "is_invoiced": False,
        }, {
            "pos_order_lines_ui_args": [(self.product_a, 1)],
            "payments": [(self.pay_later_pm, 1150)],
            "customer": self.partner_b,
            "is_invoiced": True,
        }, {
            "pos_order_lines_ui_args": [(self.product_a, 1)],
            "payments": [(self.pay_later_pm, 1150)],
            "customer": self.partner_b,
            "is_invoiced": False,
        }]

    def _create_paid_orders(self):
        orders_dict = self._create_orders(self.order_data)
        orders = self.env["pos.order"]
        for order in orders_dict.values():
            order.action_pos_order_paid()
            orders |= order
        return orders

    def _get_unreconciled_moves(self, partner):
        move_lines = self.env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_id', '=', partner.property_account_receivable_id.id),
            ('reconciled', '=', False)
        ])

        return move_lines

    def _create_settle_order_lines_data(self, due_orders):
        lines = []
        for order in due_orders:
            lines.append({'product': self.config.settle_due_product_id,
                'quantity': 1,
                'settled_order_id': order.id if not order.is_invoiced else False,
                'settled_invoice_id': order.account_move.id if order.is_invoiced else False,
                "qty": 0.0,
                "price_unit": order.amount_paid,
                "price_subtotal": 0.0,
                "price_subtotal_incl": 0.0,
                "price_type": "manual",
                "discount": 0.0,
                "refunded_qty": 0.0,
                "price_extra": 0.0
            })
        return lines

    def _create_settle_order(self, due_orders, is_invoiced=False):
        result = []
        order_data = []
        for partner_id in due_orders.mapped('partner_id'):
            partner_due_orders = due_orders.filtered(lambda o: o.partner_id.id == partner_id.id)
            total_due = sum(order.amount_paid for order in partner_due_orders)
            payments = [(self.bank_pm1, total_due)]
            payments.append((self.pay_later_pm, -total_due))
            order_data.append({
                "pos_order_lines_ui_args": self._create_settle_order_lines_data(
                    partner_due_orders
                ),
                "payments": payments,
                "customer": partner_id,
                "is_invoiced": is_invoiced,
            })
        order_data = [self.create_ui_order_data(**params) for params in order_data]
        for data in order_data:
            data['state'] = 'paid'
            data['amount_paid'] = 0

        order_ids = [order['id'] for order in self.env['pos.order'].sync_from_ui(order_data)['pos.order']]
        for order_id in self.env["pos.order"].browse(order_ids):
            result += order_id

        return result

    def _perform_test_customer_account_payment_is_reconciled(self, is_invoiced):
        session1 = self.open_new_session()
        orders = self._create_paid_orders()
        session1.close_session_from_ui()
        self.assertTrue(self._get_unreconciled_moves(self.partner_a))
        self.assertTrue(self._get_unreconciled_moves(self.partner_b))
        session2 = self.open_new_session()
        self._create_settle_order(orders, is_invoiced)
        session2.close_session_from_ui()
        self.assertFalse(self._get_unreconciled_moves(self.partner_a))
        self.assertFalse(self._get_unreconciled_moves(self.partner_b))

    def test_customer_account_payment_is_reconciled_when_settlement_order_invoiced(self):
        self._perform_test_customer_account_payment_is_reconciled(True)

    def test_customer_account_payment_is_reconciled_when_settlement_order_not_invoiced(self):
        self._perform_test_customer_account_payment_is_reconciled(False)

    def test_customer_account_payment_is_reconciled_when_settlement_on_same_session(self):
        session1 = self.open_new_session()
        orders = self._create_paid_orders()
        self._create_settle_order(orders, False)
        session1.close_session_from_ui()
        self.assertFalse(self._get_unreconciled_moves(self.partner_a))
        self.assertFalse(self._get_unreconciled_moves(self.partner_b))

    def test_different_customer_invoices_settlement_same_session_reconciled_separately(self):
        self.partner_a.property_account_receivable_id = self.partner_b.property_account_receivable_id
        invoice_a = self._create_invoice_one_line(partner_id=self.partner_a, price_unit=1000)
        invoice_b = self._create_invoice_one_line(partner_id=self.partner_b, price_unit=2000)
        (invoice_a + invoice_b).action_post()
        session1 = self.open_new_session()
        order_data = [
            {
                "pos_order_lines_ui_args": [{
                    'product': self.config.settle_invoice_product_id,
                    'quantity': 1,
                    'settled_order_id': False,
                    'settled_invoice_id': invoice_a.id,
                    "qty": 0.0,
                    "price_unit": 1000,
                    "price_subtotal": 0.0,
                    "price_subtotal_incl": 0.0,
                    "price_type": "manual",
                    "discount": 0.0,
                    "refunded_qty": 0.0,
                    "price_extra": 0.0,
                }],
                "payments": [(self.bank_pm1, 500)],
                "customer": self.partner_a,
                "is_invoiced": True,
            },
            {
                "pos_order_lines_ui_args": [{
                    'product': self.config.settle_invoice_product_id,
                    'quantity': 1,
                    'settled_order_id': False,
                    'settled_invoice_id': invoice_b.id,
                    "qty": 0.0,
                    "price_unit": 2000,
                    "price_subtotal": 0.0,
                    "price_subtotal_incl": 0.0,
                    "price_type": "manual",
                    "discount": 0.0,
                    "refunded_qty": 0.0,
                    "price_extra": 0.0
                }],
                "payments": [(self.bank_pm1, 1000)],
                "customer": self.partner_b,
                "is_invoiced": True,
            },
        ]
        order_data = [self.create_ui_order_data(**params) for params in order_data]
        order_data[0].update({
            'state': 'paid',
            'amount_total': '500',
        })
        order_data[1].update({
            'state': 'paid',
            'amount_total': '1000',
        })
        self.env['pos.order'].sync_from_ui(order_data)
        session1.close_session_from_ui()
        invoice_lines_matching = self.env['account.move.line'].search([('matching_number', '=', invoice_a.line_ids[-1].matching_number)])
        self.assertEqual(len(invoice_lines_matching.partner_id), 1, "Only aml from same partner should be reconciled together")

    def test_pos_amount_unsettled_after_session_close(self):
        """ Partially settling an invoice in the POS must leave a correct
        pos_amount_unsettled once the session is closed.

        While the session is being closed, the settle payment is reconciled
        with the invoice (lowering amount_residual_signed and marking
        pos_amount_unsettled for recomputation) before the session state is
        set to 'closed'. If any flush executes the pending recomputation in
        that window, the settle line is deducted a second time
        (residual - settled instead of residual) and, as the session state
        was not a dependency, closing the session did not correct the value.
        The flush after the reconciliation simulates that recomputation.
        """
        invoice = self._create_invoice_one_line(partner_id=self.partner_a, price_unit=1000)
        invoice.action_post()
        self.assertEqual(invoice.pos_amount_unsettled, 1000)

        session = self.open_new_session()
        order_data = self.create_ui_order_data(
            pos_order_lines_ui_args=[{
                'product': self.config.settle_invoice_product_id,
                'quantity': 1,
                'settled_order_id': False,
                'settled_invoice_id': invoice.id,
                "qty": 0.0,
                "price_unit": 700,
                "price_subtotal": 0.0,
                "price_subtotal_incl": 0.0,
                "price_type": "manual",
                "discount": 0.0,
                "refunded_qty": 0.0,
                "price_extra": 0.0,
            }],
            payments=[(self.bank_pm1, 700), (self.pay_later_pm, -700)],
            customer=self.partner_a,
        )
        order_data['state'] = 'paid'
        order_data['amount_paid'] = 0
        self.env['pos.order'].sync_from_ui([order_data])
        self.assertEqual(invoice.pos_amount_unsettled, 300)

        PosSession = self.env.registry['pos.session']
        original_reconcile = PosSession._reconcile_account_move_lines

        def reconcile_and_flush(session_self, data):
            result = original_reconcile(session_self, data)
            session_self.env['account.move'].flush_model()
            return result

        with patch.object(PosSession, '_reconcile_account_move_lines', reconcile_and_flush):
            session.close_session_from_ui()

        self.assertEqual(invoice.amount_residual_signed, 300)
        self.assertEqual(invoice.pos_amount_unsettled, 300)
        self.assertEqual(self.partner_a.invoices_amount_due, 300)

    def test_settlement_invoiced_later(self):
        session = self.open_new_session()
        order_dict = self._create_orders([{
            "pos_order_lines_ui_args": [(self.product_a, 1)],
            "payments": [(self.pay_later_pm, 1150)],
            "customer": self.partner_a,
            "is_invoiced": False,
        }])
        order = next(iter(order_dict.values()))
        order.action_pos_order_paid()
        self._create_settle_order(order, False)
        session.close_session_from_ui()
        order._generate_pos_order_invoice()
        self.assertEqual(order.state, 'done')
        self.assertEqual(order.account_move.payment_state, 'paid')
