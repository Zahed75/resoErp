from datetime import datetime

import odoo

from odoo.fields import Command
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.tests import Form


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_invoicing_after_closing_session(self):
        self.partner_moda.parent_id = self.partner_adgu
        self.pos_config_eur.payment_method_ids = [(4, self.credit_payment_method.id)]
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_no_tax.product_variant_id.id}
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 5},
                {'payment_method_id': self.credit_payment_method.id, 'amount': 5},
            ],
            'pos_config': self.pos_config_eur
        })

        current_session = self.pos_config_eur.current_session_id
        current_session.action_pos_session_closing_control()

        accounting_partner = self.env['res.partner']._find_accounting_partner(self.partner_moda)
        accounting_partner._invalidate_cache()
        self.assertEqual(accounting_partner.total_due, 5.0)
        order.action_pos_order_invoice()
        self.assertEqual(accounting_partner.total_due, 5.0)

        # get journal entry that does the reverse payment, it the ref must contains Reversal
        reverse_payment = self.env['account.move'].search([('ref', 'ilike', "Reversal")])
        original_payment = self.env['account.move'].search([('ref', '=', current_session.display_name)])
        original_customer_payment_entry = original_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        reverser_customer_payment_entry = reverse_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        # check that both use the same account
        self.assertEqual(len(reverser_customer_payment_entry), 2)
        self.assertEqual(len(original_customer_payment_entry), 2)
        self.assertTrue(order.account_move.line_ids.partner_id == self.partner_moda.commercial_partner_id)
        self.assertEqual(reverser_customer_payment_entry[0].balance, -5.0)
        self.assertEqual(reverser_customer_payment_entry[1].balance, -5.0)
        self.assertEqual(reverser_customer_payment_entry[0].amount_currency, -5.0)
        self.assertEqual(reverser_customer_payment_entry[1].amount_currency, -5.0)
        self.assertEqual(original_customer_payment_entry.account_id.id, reverser_customer_payment_entry.account_id.id)
        self.assertEqual(reverser_customer_payment_entry.partner_id, original_customer_payment_entry.partner_id)

    def test_get_total_due_in_pos_currency(self):
        """ get_total_due must return an amount expressed in the PoS currency.

        The accounting due (res.partner.total_due) is in company currency and
        must be converted, while the pay later payments of the still open
        sessions are already in the PoS currency and must not be converted.
        """
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        self.pos_config_usd.write({
            'payment_method_ids': [(4, self.customer_account_payment_method.id, 0)],
        })
        # PoS runs in another currency than the company one: 1 company = 0.5 other
        self.other_currency = self.setup_other_currency("EUR", rounding=0.01, rates=[(datetime.today().date(), 0.5)])
        self.pos_config_usd.journal_id.write({
            'currency_id': self.other_currency.id
        })
        other_pricelist = self.env['product.pricelist'].create({
            'name': 'Public Pricelist Other',
            'currency_id': self.other_currency.id,
        })
        self.pos_config_usd.write({
            'pricelist_id': other_pricelist.id,
            'available_pricelist_ids': [(6, 0, other_pricelist.ids)],
        })
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_moda.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 100,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
            })],
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'amount_paid': 100.0,
            'amount_total': 100.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })
        self.assertEqual(order.currency_id, self.other_currency)

        # pay the whole order with the customer account
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 100.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        # The session is still open: nothing is accounted yet, the due only comes
        # from the pay later payment, which is already in the PoS currency.
        self.assertEqual(self.partner_moda.total_due, 0.0)
        self.assertEqual(self.partner_moda.get_total_due(self.pos_config_usd.id)['res.partner'][0]['total_due'], 100.0)

        # Once the session is closed the due comes from accounting, in company
        # currency, and must be converted back to the PoS currency.
        current_session.action_pos_session_closing_control()
        self.partner_moda.invalidate_recordset(['total_due'])
        self.assertEqual(self.partner_moda.total_due, 200.0)
        self.assertEqual(self.partner_moda.get_total_due(self.pos_config_usd.id)['res.partner'][0]['total_due'], 100.0)

        # Both sources add up, each one in the PoS currency.
        self.pos_config_usd.open_ui()
        new_session = self.pos_config_usd.current_session_id
        new_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': new_session.id,
            'partner_id': self.partner_moda.id,
            'lines': [(0, 0, {
                'name': "OL/0002",
                'product_id': self.product1.id,
                'price_unit': 50,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 50,
                'price_subtotal_incl': 50,
            })],
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'amount_paid': 50.0,
            'amount_total': 50.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })
        payment_context = {"active_ids": new_order.ids, "active_id": new_order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 50.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.assertEqual(self.partner_moda.get_total_due(self.pos_config_usd.id)['res.partner'][0]['total_due'], 150.0)

    def test_invoicing_after_closing_session_intermediary_account(self):
        """ Test that an invoice can be created after the session is closed """
        receivable_account = self.env.company.account_default_pos_receivable_account_id.copy()
        self.cash_payment_method.receivable_account_id = receivable_account
        self.partner_moda.parent_id = self.partner_adgu

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_no_tax.product_variant_id.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': 10},
            ],
        })

        current_session = self.pos_config_usd.current_session_id
        current_session.action_pos_session_closing_control()
        accounting_partner = self.env['res.partner']._find_accounting_partner(self.partner_moda)
        self.assertEqual(accounting_partner.total_due, 0.0)

        # create invoice
        order.action_pos_order_invoice()
        self.assertEqual(accounting_partner.total_due, 0.0)

        # get journal entry that does the reverse payment, it the ref must contains Reversal
        reverse_payment = self.env['account.move'].search([('ref', 'ilike', "Reversal")])
        original_payment = self.env['account.move'].search([('ref', '=', current_session.display_name)])
        original_customer_payment_entry = original_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        reverser_customer_payment_entry = reverse_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        # check that both use the same account
        self.assertEqual(original_customer_payment_entry.account_id, receivable_account)
        self.assertEqual(original_customer_payment_entry.account_id.id, reverser_customer_payment_entry.account_id.id)
        self.assertEqual(reverser_customer_payment_entry.partner_id, original_customer_payment_entry.partner_id)
        aml_receivable = self.env['account.move.line'].formatted_read_group([('account_type', '=', 'asset_receivable')], groupby=['matching_number'], aggregates=['__count'])
        self.assertEqual(len(aml_receivable), 3)
        for aml_g in aml_receivable:
            self.assertEqual(aml_g['__count'], 2)

    def test_payment_order_does_not_set_negative_customer_due_total(self):
        """A payment order (negative pay_later amount) must not set customer_due_total < 0.
        Before the fix, this caused pos_orders_amount_due to go negative, inflating
        remainingDue in the frontend and showing a wrong settle-due amount."""
        self.pos_config_eur.payment_method_ids = [(4, self.credit_payment_method.id)]

        charge_order, _ = self.create_backend_pos_order({
            'order_data': {'partner_id': self.partner_moda.id},
            'line_data': [{'product_id': self.ten_dollars_no_tax.product_variant_id.id}],
            'payment_data': [{'payment_method_id': self.credit_payment_method.id, 'amount': 10}],
            'pos_config': self.pos_config_eur,
        })
        self.assertEqual(charge_order.customer_due_total, 10.0)

        session = self.pos_config_eur.current_session_id
        payment_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session.id,
            'partner_id': self.partner_moda.id,
            'amount_paid': -10.0,
            'amount_total': -10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'payment_ids': [Command.create({
                'amount': -10.0,
                'payment_method_id': self.credit_payment_method.id,
            })],
        })
        payment_order.write({'state': 'paid'})
        self.assertEqual(payment_order.customer_due_total, 0.0)

        accounting_partner = self.env['res.partner']._find_accounting_partner(self.partner_moda)
        accounting_partner.invalidate_recordset(['pos_orders_amount_due'])
        self.assertEqual(accounting_partner.pos_orders_amount_due, 10.0)

    def test_has_moves_after_full_settle(self):
        """ has_moves should stay True for a fully-settled pay-later customer (no invoice). """
        self.pos_config_usd.payment_method_ids = [(4, self.credit_payment_method.id)]
        order, _ = self.create_backend_pos_order({
            'order_data': {'partner_id': self.partner_moda.id},
            'line_data': [{'product_id': self.ten_dollars_no_tax.product_variant_id.id}],
            'payment_data': [{'payment_method_id': self.credit_payment_method.id, 'amount': 10}],
        })
        current_session = self.pos_config_usd.current_session_id

        settle_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_moda.id,
            'lines': [(0, 0, {
                'name': "SL/0001",
                'product_id': self.pos_config_usd.settle_due_product_id.id,
                'price_unit': 10,
                'qty': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'settled_order_id': order.id,
            })],
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'amount_paid': 0.0,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })
        settle_order.add_payment({'pos_order_id': settle_order.id, 'amount': 10, 'payment_method_id': self.bank_payment_method.id})
        settle_order.add_payment({'pos_order_id': settle_order.id, 'amount': -10, 'payment_method_id': self.credit_payment_method.id})
        settle_order.state = 'paid'

        current_session.action_pos_session_closing_control()
        self.assertEqual(self.partner_moda.total_due, 0)
        self.assertEqual(self.partner_moda.has_moves, True)

    def test_deleted_partner_get_all_total_due(self):
        """ Test that get_all_total_due works when some partners have been deleted """
        partner_a = self.env["res.partner"].create({"name": "A Partner"})
        partner_b = self.env["res.partner"].create({"name": "B Partner"})
        partner_c = self.env["res.partner"].create({"name": "C Partner"})

        partners = self.env['res.partner'].browse([partner_a.id, partner_b.id, partner_c.id])

        partner_b.unlink()
        self.assertEqual(len(partners.get_all_total_due(self.pos_config_usd.id)), 2)

    def test_matching_orders_and_refunds_using_pay_later_pm_full_match(self):
        """ Testing get_matching_paylater_orders.
        It needs to return the list of orders to hide. In this case both the
        order and the full refund needs to be returned as the amounts paid using
        the customer account amounts to 0 in total.
        """
        partner = self.env["res.partner"].create({"name": "Partner"})
        self.pos_config_usd.payment_method_ids = [(4, self.credit_payment_method.id)]

        order, refund = self.create_backend_pos_order({
            'order_data': {
                'partner_id': partner.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 30},
            ],
            'refund_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': -30},
            ]
        })

        matching_orders = partner.get_matching_paylater_orders()
        self.assertIn(order.id, matching_orders)
        self.assertIn(refund.id, matching_orders)

    def test_matching_orders_and_refunds_using_pay_later_pm_no_match(self):
        """ Testing get_matching_paylater_orders.
        It needs to return the list of orders to hide. In this case nothing needs
        to be returned as the amount paid using the customer account amounts to 10 in total.
        """
        partner = self.env["res.partner"].create({"name": "Partner"})
        self.pos_config_usd.payment_method_ids = [(4, self.credit_payment_method.id)]

        self.create_backend_pos_order({
            'order_data': {
                'partner_id': partner.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 30},
            ],
            'refund_data': [
                {'payment_method_id': self.cash_payment_method.id, 'amount': -10},
                {'payment_method_id': self.credit_payment_method.id, 'amount': -20},
            ]
        })

        matching_orders = partner.get_matching_paylater_orders()
        self.assertEqual(len(matching_orders), 0)

    def test_matching_orders_and_refunds_using_pay_later_pm_partial_refunds_match(self):
        """ Testing get_matching_paylater_orders.
        It needs to return the list of orders to hide.
        First we have a partial refund. The total using the customer account is not 0.
        Therefore the function should return an empty string.

        Later the rest is refunded on the customer account. This time the function
        should return the order and both refund since the total on the customer account
        is 0.
        """
        partner = self.env["res.partner"].create({"name": "Partner"})
        self.pos_config_usd.payment_method_ids = [(4, self.credit_payment_method.id)]

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': partner.id,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
                {'product_id': self.twenty_dollars_with_15_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.credit_payment_method.id, 'amount': 30},
            ],
        })

        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                line.qty = 0
        refund = refund_form.save()

        self.assertEqual(refund.amount_total, -20.0)

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.credit_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()

        matching_orders = partner.get_matching_paylater_orders()
        self.assertEqual(len(matching_orders), 0)

        refund_action = order.refund()
        remaining_refund = self.env['pos.order'].browse(refund_action['res_id'])
        self.assertEqual(remaining_refund.amount_total, -10.0)

        payment_context = {"active_ids": remaining_refund.ids, "active_id": remaining_refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': remaining_refund.amount_total,
            'payment_method_id': self.credit_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()

        matching_orders = partner.get_matching_paylater_orders()
        self.assertIn(order.id, matching_orders)
        self.assertIn(refund.id, matching_orders)
        self.assertIn(remaining_refund.id, matching_orders)
