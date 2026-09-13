# -*- coding: utf-8 -*-
from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools.float_utils import float_compare


class TestOwnership(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Registry = cls.env['reso.owner.registry']
        cls.Transfer = cls.env['reso.share.transfer']
        cls.Run = cls.env['reso.distribution.run']
        cls.Property = cls.env['reso.property']
        cls.property_main = cls.Property.create({
            'name': 'Test Ownership Resort',
            'code': 'TOR',
        })
        cls.partner_a = cls.env['res.partner'].create({'name': 'Owner A'})
        cls.partner_b = cls.env['res.partner'].create({'name': 'Owner B'})
        cls.partner_c = cls.env['res.partner'].create({'name': 'Owner C'})
        cls.partner_d = cls.env['res.partner'].create({'name': 'Owner D'})
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Test Ownership Manager',
            'login': 'test_ownership_manager@test',
            'company_id': cls.env.company.id,
            'company_ids': [Command.link(cls.env.company.id)],
            'group_ids': [Command.set([
                cls.env.ref('reso_ownership.group_ownership_manager').id,
            ])],
        })

    def _create_registry(self, partner, fraction, property=None, **kwargs):
        values = {
            'property_id': (property or self.property_main).id,
            'partner_id': partner.id,
            'share_class': 'fraction',
            'fraction_percent': fraction,
        }
        values.update(kwargs)
        return self.Registry.create(values)

    def test_01_registry_sequence(self):
        registry = self._create_registry(self.partner_a, 10.0)
        self.assertNotEqual(registry.certificate_number, 'New')
        self.assertTrue(
            registry.certificate_number.startswith('SH/'),
            'Certificate number must come from the SH/ sequence.')

    def test_02_fraction_total_cannot_exceed_100(self):
        self._create_registry(self.partner_a, 60.0)
        with self.assertRaises(ValidationError):
            self._create_registry(self.partner_b, 50.0)

    def test_03_transfer_complete_moves_fraction(self):
        source = self._create_registry(self.partner_a, 100.0)
        transfer = self.Transfer.create({
            'registry_id': source.id,
            'to_partner_id': self.partner_b.id,
            'fraction_percent': 40.0,
            'consideration_amount': 40000.0,
        })
        transfer.action_submit()
        transfer.with_user(self.manager_user).action_approve()
        transfer.action_complete()
        self.assertEqual(transfer.state, 'completed')
        self.assertEqual(source.fraction_percent, 60.0)
        self.assertEqual(source.status, 'active')
        target = self.Registry.search([
            ('property_id', '=', self.property_main.id),
            ('partner_id', '=', self.partner_b.id),
        ])
        self.assertEqual(len(target), 1)
        self.assertEqual(target.fraction_percent, 40.0)
        # Transfer the remainder: source must be fully redeemed.
        transfer2 = self.Transfer.create({
            'registry_id': source.id,
            'to_partner_id': self.partner_c.id,
            'fraction_percent': 60.0,
        })
        transfer2.action_submit()
        transfer2.with_user(self.manager_user).action_approve()
        transfer2.action_complete()
        self.assertEqual(source.fraction_percent, 0.0)
        self.assertEqual(source.status, 'redeemed')

    def test_04_transfer_exceeding_remaining_fraction(self):
        source = self._create_registry(self.partner_a, 100.0)
        transfer = self.Transfer.create({
            'registry_id': source.id,
            'to_partner_id': self.partner_b.id,
            'fraction_percent': 150.0,
        })
        transfer.action_submit()
        transfer.with_user(self.manager_user).action_approve()
        with self.assertRaises(UserError):
            transfer.action_complete()

    def test_05_distribution_calculate_exact_split(self):
        self._create_registry(self.partner_a, 60.0)
        self._create_registry(self.partner_b, 40.0)
        run = self.Run.create({
            'property_id': self.property_main.id,
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'total_amount': 100000.0,
        })
        run.action_calculate()
        self.assertEqual(run.state, 'calculated')
        amounts = {line.partner_id: line.amount for line in run.line_ids}
        self.assertEqual(len(run.line_ids), 2)
        self.assertEqual(amounts[self.partner_a], 60000.0)
        self.assertEqual(amounts[self.partner_b], 40000.0)
        total_distributed = sum(run.line_ids.mapped('amount'))
        self.assertEqual(
            float_compare(total_distributed, 100000.0,
                          precision_rounding=0.01),
            0,
            'Lines must sum exactly to the pool amount.')

    def test_06_distribution_calculate_rounding_residual(self):
        property2 = self.Property.create({
            'name': 'Rounding Resort',
            'code': 'RR1',
        })
        self._create_registry(self.partner_a, 33.33, property=property2)
        self._create_registry(self.partner_b, 33.33, property=property2)
        self._create_registry(self.partner_c, 33.34, property=property2)
        run = self.Run.create({
            'property_id': property2.id,
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'total_amount': 99999.99,
        })
        run.action_calculate()
        self.assertEqual(len(run.line_ids), 3)
        total_distributed = sum(run.line_ids.mapped('amount'))
        self.assertEqual(
            float_compare(total_distributed, 99999.99,
                          precision_rounding=0.01),
            0,
            'Lines (incl. rounding residual) must sum exactly to the pool.')
        for line in run.line_ids:
            self.assertGreaterEqual(line.amount, 0.0)

    def test_07_approve_requires_manager_group(self):
        self._create_registry(self.partner_a, 100.0)
        run = self.Run.create({
            'property_id': self.property_main.id,
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'total_amount': 1000.0,
        })
        run.action_calculate()
        user = self.env['res.users'].create({
            'name': 'Plain Ownership User',
            'login': 'plain_ownership_user@test',
            'company_id': self.env.company.id,
            'company_ids': [Command.link(self.env.company.id)],
            'group_ids': [Command.set([
                self.env.ref('reso_ownership.group_ownership_user').id,
            ])],
        })
        with self.assertRaises(UserError):
            run.with_user(user).action_approve()
        # Sanity check: an actual manager can approve.
        manager = self.env['res.users'].create({
            'name': 'Ownership Manager',
            'login': 'ownership_manager@test',
            'company_id': self.env.company.id,
            'company_ids': [Command.link(self.env.company.id)],
            'group_ids': [Command.set([
                self.env.ref(
                    'reso_ownership.group_ownership_manager').id,
            ])],
        })
        run.with_user(manager).action_approve()
        self.assertEqual(run.state, 'approved')

    def test_08_period_end_must_follow_start(self):
        self._create_registry(self.partner_a, 100.0)
        with self.assertRaises(ValidationError):
            self.Run.create({
                'property_id': self.property_main.id,
                'period_start': '2026-03-31',
                'period_end': '2026-03-31',
                'total_amount': 1000.0,
            })
