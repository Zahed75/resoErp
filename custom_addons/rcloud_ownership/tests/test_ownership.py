# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRcloudOwnership(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.property = cls.env['rcloud.property'].create({
            'name': 'Ownership Test Resort',
            'code': 'OTR',
        })
        cls.share_class = cls.env['rcloud.share.class'].create({
            'name': 'Class A',
            'property_id': cls.property.id,
            'total_units': 100,
            'unit_nominal_value': 1000.0,
            'distribution_rule': 'gross_room_revenue',
        })
        cls.period_start = date(2026, 1, 1)
        cls.period_end = date(2026, 1, 31)  # 30-day period

    def _owner(self, name):
        partner = self.env['res.partner'].create({'name': name})
        return self.env['rcloud.owner'].create({'partner_id': partner.id})

    def _holding(self, owner, units, acquired):
        return self.env['rcloud.share.holding'].create({
            'owner_id': owner.id,
            'share_class_id': self.share_class.id,
            'units_held': units,
            'acquired_date': acquired,
        })

    def _run(self, total_amount, basis='gross_room_revenue'):
        return self.env['rcloud.distribution.run'].create({
            'property_id': self.property.id,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'revenue_basis': basis,
            'total_amount': total_amount,
        })

    # --------------------------------------------------------- weighting
    def test_mid_period_acquisition_weighting(self):
        """X acquires 10 units at start+10 (10*20=200 weighted), Y holds
        10 units all period (10*30=300) → 200/500 vs 300/500."""
        owner_x = self._owner('Owner X')
        owner_y = self._owner('Owner Y')
        self._holding(owner_x, 10, date(2026, 1, 11))
        self._holding(owner_y, 10, date(2025, 12, 1))

        Holding = self.env['rcloud.share.holding']
        self.assertEqual(
            Holding.get_weighted_units(
                owner_x, self.share_class,
                self.period_start, self.period_end), 200)
        self.assertEqual(
            Holding.get_weighted_units(
                owner_y, self.share_class,
                self.period_start, self.period_end), 300)
        self.assertEqual(
            Holding.get_holding_on(
                owner_x, self.share_class, date(2026, 1, 10)), 0)
        self.assertEqual(
            Holding.get_holding_on(
                owner_x, self.share_class, date(2026, 1, 11)), 10)

        run = self._run(500.0)
        run.action_calculate()
        line_x = run.line_ids.filtered(lambda l: l.owner_id == owner_x)
        line_y = run.line_ids.filtered(lambda l: l.owner_id == owner_y)
        self.assertAlmostEqual(line_x.net_payable, 200.0, places=2)
        self.assertAlmostEqual(line_y.net_payable, 300.0, places=2)
        self.assertAlmostEqual(line_x.share_pct, 40.0, places=4)
        self.assertAlmostEqual(line_y.share_pct, 60.0, places=4)

    def test_basis_amount_from_accounting(self):
        """The revenue basis is pulled from posted analytic journal items."""
        owner = self._owner('Basis Owner')
        self._holding(owner, 10, date(2025, 12, 1))
        income = self.env['account.account'].create({
            'name': 'Room Revenue',
            'code': 'REV',
            'account_type': 'income',
        })
        expense = self.env['account.account'].create({
            'name': 'Operating Expense',
            'code': 'OPE',
            'account_type': 'expense',
        })
        bank = self.env['account.account'].create({
            'name': 'Test Bank',
            'code': 'BNK',
            'account_type': 'asset_cash',
        })
        payable = self.env['account.account'].create({
            'name': 'Basis Payable',
            'code': 'BPB',
            'account_type': 'liability_payable',
        })
        journal = self.env['account.journal'].create({
            'name': 'Ownership Test', 'type': 'general', 'code': 'OTJ',
        })
        analytic = self.property.analytic_account_id
        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': date(2026, 1, 15),
            'line_ids': [
                (0, 0, {'account_id': bank.id, 'debit': 1000.0,
                        'credit': 0.0,
                        'analytic_distribution': {str(analytic.id): 100}}),
                (0, 0, {'account_id': income.id, 'debit': 0.0,
                        'credit': 1000.0,
                        'analytic_distribution': {str(analytic.id): 100}}),
                (0, 0, {'account_id': expense.id, 'debit': 200.0,
                        'credit': 0.0,
                        'analytic_distribution': {str(analytic.id): 100}}),
                (0, 0, {'account_id': payable.id, 'debit': 0.0,
                        'credit': 200.0}),
            ],
        })
        move.action_post()
        run = self._run(0.0)
        run.action_calculate()
        self.assertAlmostEqual(run.basis_amount, 1000.0, places=2)
        # NOI subtracts expense-group lines.
        run_noi = self._run(0.0, basis='noi')
        run_noi.action_calculate()
        self.assertAlmostEqual(run_noi.basis_amount, 800.0, places=2)
        # Empty pool defaults to the computed basis.
        self.assertAlmostEqual(run.total_amount, 1000.0, places=2)

    def test_transfer_mid_period_moves_weighting(self):
        owner_a = self._owner('Owner A')
        owner_b = self._owner('Owner B')
        self._holding(owner_a, 10, date(2025, 12, 1))
        transfer = self.env['rcloud.share.transfer'].create({
            'from_owner_id': owner_a.id,
            'to_owner_id': owner_b.id,
            'share_class_id': self.share_class.id,
            'units': 10,
            'transfer_date': date(2026, 1, 16),  # start + 15
        })
        transfer.action_submit()
        transfer.action_approve()
        transfer.action_complete()

        Holding = self.env['rcloud.share.holding']
        self.assertEqual(
            Holding.get_holding_on(owner_a, self.share_class,
                                   date(2026, 1, 15)), 10)
        self.assertEqual(
            Holding.get_holding_on(owner_a, self.share_class,
                                   date(2026, 1, 16)), 0)
        self.assertEqual(
            Holding.get_holding_on(owner_b, self.share_class,
                                   date(2026, 1, 16)), 10)
        self.assertEqual(
            Holding.get_weighted_units(
                owner_a, self.share_class,
                self.period_start, self.period_end), 150)
        self.assertEqual(
            Holding.get_weighted_units(
                owner_b, self.share_class,
                self.period_start, self.period_end), 150)

        run = self._run(300.0)
        run.action_calculate()
        line_a = run.line_ids.filtered(lambda l: l.owner_id == owner_a)
        line_b = run.line_ids.filtered(lambda l: l.owner_id == owner_b)
        self.assertAlmostEqual(line_a.net_payable, 150.0, places=2)
        self.assertAlmostEqual(line_b.net_payable, 150.0, places=2)

    def test_over_transfer_rejected(self):
        owner_a = self._owner('Owner A')
        self._holding(owner_a, 5, date(2025, 12, 1))
        transfer = self.env['rcloud.share.transfer'].create({
            'from_owner_id': owner_a.id,
            'to_owner_id': self._owner('Owner B').id,
            'share_class_id': self.share_class.id,
            'units': 10,
            'transfer_date': date(2026, 1, 10),
        })
        transfer.action_submit()
        transfer.action_approve()
        with self.assertRaises(UserError):
            transfer.action_complete()

    def test_transfer_approve_requires_manager(self):
        staff = self.env['res.users'].create({
            'name': 'Staff No Manager',
            'login': 'staff_no_manager_ownership',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'group_ids': [(4, self.env.ref('rcloud_base.group_hotel_user').id)],
        })
        transfer = self.env['rcloud.share.transfer'].create({
            'from_owner_id': self._owner('Owner A').id,
            'to_owner_id': self._owner('Owner B').id,
            'share_class_id': self.share_class.id,
            'units': 1,
            'transfer_date': date(2026, 1, 10),
        })
        transfer.action_submit()
        with self.assertRaises(UserError):
            transfer.with_user(staff).action_approve()

    # ------------------------------------------------------------ rounding
    def test_rounding_cent_exact(self):
        """300 owners x 1 unit, pool 1000.00: sum(net_payable) must equal
        the distributable amount to the cent, exactly."""
        partners = self.env['res.partner'].create(
            [{'name': 'Owner %03d' % i} for i in range(300)])
        owners = self.env['rcloud.owner'].create(
            [{'partner_id': p.id} for p in partners])
        self.env['rcloud.share.holding'].create([{
            'owner_id': o.id,
            'share_class_id': self.share_class.id,
            'units_held': 1,
            'acquired_date': date(2025, 12, 1),
        } for o in owners])

        run = self._run(1000.0)
        run.action_calculate()
        self.assertEqual(len(run.line_ids), 300)
        self.assertEqual(
            round(sum(run.line_ids.mapped('net_payable')), 2),
            round(run.distributable_amount, 2))
        self.assertEqual(
            round(sum(run.line_ids.mapped('net_payable')), 2), 1000.0)
        # Residual parked on the largest line: 299 x 3.33 + 1 x 4.33.
        nets = sorted(run.line_ids.mapped('net_payable'))
        self.assertAlmostEqual(nets[0], 3.33, places=2)
        self.assertAlmostEqual(nets[-1], 4.33, places=2)

        # With deductions the same invariant holds.
        self.share_class.write({
            'management_fee_pct': 10.0, 'reserve_pct': 5.0})
        run2 = self._run(1000.0)
        run2.action_calculate()
        self.assertAlmostEqual(run2.deduction_amount, 150.0, places=2)
        self.assertEqual(
            round(sum(run2.line_ids.mapped('net_payable')), 2),
            round(run2.distributable_amount, 2))
        self.assertEqual(
            round(sum(run2.line_ids.mapped('net_payable')), 2), 850.0)

    # ------------------------------------------------------ portal isolation
    def _portal_user(self, login):
        return self.env['res.users'].create({
            'name': login,
            'login': login,
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'group_ids': [(4, self.env.ref('base.group_portal').id)],
        })

    def test_portal_isolation(self):
        """Portal user A must not read owner B's distribution line."""
        user_a = self._portal_user('portal_owner_a')
        user_b = self._portal_user('portal_owner_b')
        owner_a = self._owner('Owner A')
        owner_b = self._owner('Owner B')
        owner_a.portal_user_id = user_a
        owner_b.portal_user_id = user_b
        self._holding(owner_a, 10, date(2025, 12, 1))
        self._holding(owner_b, 10, date(2025, 12, 1))

        run = self._run(100.0)
        run.action_calculate()
        line_a = run.line_ids.filtered(lambda l: l.owner_id == owner_a)
        line_b = run.line_ids.filtered(lambda l: l.owner_id == owner_b)

        env_a = self.env(
            user=user_a,
            context={'allowed_company_ids': [self.company.id]},
        )
        # A sees exactly their own line...
        visible = env_a['rcloud.distribution.line'].search([])
        self.assertEqual(visible, line_a)
        # ...and reading B's line raises AccessError.
        with self.assertRaises(AccessError):
            env_a['rcloud.distribution.line'].browse(line_b.id).read()
        with self.assertRaises(AccessError):
            env_a['rcloud.owner'].browse(owner_b.id).read()
        with self.assertRaises(AccessError):
            env_a['rcloud.share.holding'].browse(
                line_b.owner_id.holding_ids[0].id).read()

    # ------------------------------------------------------ run lifecycle
    def test_run_lifecycle_to_posted(self):
        expense = self.env['account.account'].create({
            'name': 'Distribution Expense',
            'code': 'DEX',
            'account_type': 'expense',
        })
        self.share_class.write({
            'management_fee_pct': 10.0,
            'expense_account_id': expense.id,
        })
        payable = self.env['account.account'].create({
            'name': 'Owners Payable',
            'code': 'OPA',
            'account_type': 'liability_payable',
        })
        bank_acc = self.env['account.account'].create({
            'name': 'Owners Bank',
            'code': 'OBA',
            'account_type': 'asset_cash',
        })
        self.env['account.journal'].create({
            'name': 'Ownership General', 'type': 'general', 'code': 'OGJ',
        })
        self.env['account.journal'].create({
            'name': 'Ownership Bank', 'type': 'bank', 'code': 'OBJ',
            'default_account_id': bank_acc.id,
        })

        owner = self._owner('Owner A')
        owner.partner_id.write({'email': 'owner-a@example.com'})
        self._holding(owner, 10, date(2025, 12, 1))
        run = self._run(1000.0)
        run.action_calculate()
        self.assertEqual(run.state, 'computed')
        self.assertAlmostEqual(run.distributable_amount, 900.0, places=2)

        run.action_approve()
        self.assertEqual(run.state, 'approved')
        run.action_post()
        self.assertEqual(run.state, 'posted')
        line = run.line_ids
        self.assertTrue(line.move_id)
        self.assertEqual(line.move_id.state, 'posted')
        debit_line = line.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = line.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, expense)
        self.assertEqual(
            credit_line.account_id.account_type, 'liability_payable')
        self.assertEqual(credit_line.partner_id, owner.partner_id)
        self.assertAlmostEqual(debit_line.debit, 900.0, places=2)

        # Posted runs are immutable.
        with self.assertRaises(UserError):
            run.action_calculate()
        with self.assertRaises(UserError):
            run.action_approve()

        run.action_mark_paid()
        self.assertEqual(run.state, 'paid')
        self.assertTrue(line.payment_id)
        self.assertEqual(line.payment_id.amount, 900.0)
        self.assertEqual(line.payment_id.payment_type, 'outbound')
        self.assertEqual(line.state, 'paid')

    def test_report_template_rows_and_csv(self):
        owner = self._owner('Owner A')
        self._holding(owner, 10, date(2025, 12, 1))
        run = self._run(100.0)
        run.action_calculate()
        run.action_approve()
        run.action_post()

        template = self.env['rcloud.owner.report.template'].create({
            'name': '2026 January',
            'date_from': date(2026, 1, 1),
            'date_to': date(2026, 1, 31),
            'grouping': 'property',
        })
        rows = template.get_report_rows()
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]['net'], 100.0, places=2)
        csv_data = template.render_csv()
        self.assertIn('Ownership Test Resort', csv_data)
        self.assertIn('100.0', csv_data)

        # A portal user running the template is forced to their own lines.
        user = self._portal_user('portal_owner_report')
        owner.portal_user_id = user
        template_env = template.with_user(user)
        self.assertEqual(len(template_env.get_report_rows()), 1)
