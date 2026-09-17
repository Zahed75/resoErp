# -*- coding: utf-8 -*-
import psycopg2

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRcloudBase(TransactionCase):

    def test_property_creation_provisions_analytic_account(self):
        prop = self.env['rcloud.property'].create({
            'name': 'Test Beach Resort',
            'code': 'TBR',
        })
        self.assertTrue(prop.analytic_account_id,
                        "An analytic account must be auto-created")
        self.assertEqual(prop.analytic_account_id.plan_id.name, 'Property')
        self.assertEqual(prop.analytic_account_id.company_id, prop.company_id)

    def test_property_code_unique_per_company(self):
        self.env['rcloud.property'].create({'name': 'A', 'code': 'DUP'})
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.env['rcloud.property'].create({'name': 'B', 'code': 'DUP'})

    def test_multi_company_record_rule(self):
        company_b = self.env['res.company'].create({'name': 'Company B'})
        prop_b = self.env['rcloud.property'].with_company(company_b).create({
            'name': 'Other Resort', 'code': 'OTH',
        })
        # ir.rules do not apply to the superuser the test runner uses, so
        # assert isolation as a regular hotel-staff user of Company A.
        user_a = self.env['res.users'].create({
            'name': 'Staff A',
            'login': 'staff_a_%d' % self.env.company.id,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(4, self.env.ref('rcloud_base.group_hotel_user').id)],
        })
        env_a = self.env(
            user=user_a,
            context={'allowed_company_ids': [self.env.company.id]},
        )
        visible = env_a['rcloud.property'].search([('code', '=', 'OTH')])
        self.assertFalse(visible,
                         "Property B must be invisible to Company A staff")

    def test_second_property_reuses_plan(self):
        p1 = self.env['rcloud.property'].create({'name': 'P1', 'code': 'P1'})
        p2 = self.env['rcloud.property'].create({'name': 'P2', 'code': 'P2'})
        self.assertEqual(p1.analytic_account_id.plan_id,
                         p2.analytic_account_id.plan_id,
                         "All properties share the single Property plan")
