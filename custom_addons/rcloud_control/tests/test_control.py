# -*- coding: utf-8 -*-
import os
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.rcloud_control.models import provision_utils
from odoo.addons.rcloud_control.models.provision_job import sign_entitlement


@tagged('post_install', '-at_install')
class TestTenant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env['rcloud.plan'].create({
            'name': 'Starter', 'monthly_price': 9900.0,
            'max_properties': 1, 'max_rooms': 20, 'max_users': 5,
        })
        cls.big_plan = cls.env['rcloud.plan'].create({
            'name': 'Resort', 'monthly_price': 49900.0,
            'max_properties': 5, 'max_rooms': 100, 'max_users': 50,
        })

    def _create(self, **kw):
        vals = {
            'name': 'Acme Resorts', 'subdomain': 'acme',
            'db_name': 'rcloud_acme', 'plan_id': self.plan.id,
        }
        vals.update(kw)
        return self.env['rcloud.tenant'].create(vals)

    def test_subdomain_validation(self):
        for good in ('abc', 'a-b', 'hotel42', 'x' + 'y' * 30 + 'z'):
            self._create(subdomain=good, db_name='rcloud_%s' % good[:10])
        for bad in ('-abc', 'abc-', 'Abc', 'ab', 'a' * 33, 'www',
                    'admin', 'api', 'app', 'mail', 'static', 'with space'):
            with self.assertRaises(ValidationError, msg=bad):
                self._create(subdomain=bad, db_name='rcloud_bad_%d' % (
                    abs(hash(bad)) % 100000))

    def test_check_limits(self):
        tenant = self._create(room_count=10, user_count=3)
        self.assertTrue(tenant.check_limits())
        tenant.room_count = 25
        with self.assertRaises(ValidationError):
            tenant.check_limits()
        # Upgrading the plan clears the violation.
        tenant.plan_id = self.big_plan
        self.assertTrue(tenant.check_limits())

    def test_extend_trial_and_suspend_resume(self):
        tenant = self._create()
        tenant.state = 'trial'
        tenant.trial_ends = '2026-09-01'
        tenant.action_extend_trial()
        self.assertEqual(str(tenant.trial_ends), '2026-09-15')
        tenant.action_suspend()
        self.assertEqual(tenant.state, 'suspended')
        tenant.action_resume()
        self.assertEqual(tenant.state, 'active')

    def test_impersonation_log_immutable(self):
        tenant = self._create()
        tenant.action_impersonate()
        log = self.env['rcloud.impersonation.log'].search([
            ('tenant_id', '=', tenant.id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.admin_user_id, self.env.user)
        with self.assertRaises(UserError):
            log.unlink()

    def test_sign_entitlement_control_plane(self):
        blob = sign_entitlement('trial', None, 'acme')
        payload, _, signature = blob.rpartition('.')
        self.assertEqual(payload, 'trial||acme')
        self.assertEqual(len(signature), 64)


@tagged('post_install', '-at_install')
class TestProvisioningRollback(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env['rcloud.plan'].create({
            'name': 'Starter', 'monthly_price': 9900.0,
        })

    def _db_exists(self, db_name):
        with provision_utils.admin_cursor() as cr:
            return provision_utils.database_exists(cr, db_name)

    def test_rollback_drops_database_on_step_failure(self):
        import os
        db_name = 'rcloud_prov_test_%d' % os.getpid()
        tenant = self.env['rcloud.tenant'].create({
            'name': 'Rollback Tenant', 'subdomain': 'rollback',
            'db_name': db_name, 'plan_id': self.plan.id,
        })
        Job = self.env['rcloud.provision.job']

        def fake_create_database(db_name, template=None):
            # Create a real (plain) database so rollback has something to
            # drop, without needing the rcloud_template template DB.
            return provision_utils_create(db_name)

        provision_utils_create = provision_utils.create_database

        self.assertFalse(self._db_exists(db_name))
        # The template filestore must exist for the copy step to be
        # reached; the actual copytree is patched to explode below.
        from odoo.tools import config
        source = os.path.join(
            config['data_dir'], 'filestore', 'rcloud_template')
        os.makedirs(source, exist_ok=True)
        try:
            with patch.object(
                    provision_utils, 'create_database',
                    fake_create_database), \
                 patch('odoo.addons.rcloud_control.models.provision_job.'
                       'shutil.copytree',
                       side_effect=RuntimeError('filestore copy exploded')):
                job = Job.create({'tenant_id': tenant.id})
                job.action_run()
            self.assertEqual(job.state, 'failed')
            self.assertEqual(job.step, 'copy_filestore')
            step = job.step_ids.filtered(
                lambda s: s.name == 'copy_filestore')
            self.assertEqual(step.state, 'failed')
            self.assertIn('exploded', step.log)
            self.assertIn('FAILED', job.log)
            # Rollback dropped the database created by the first step.
            self.assertFalse(self._db_exists(db_name))
        finally:
            provision_utils.drop_database(db_name)
            if os.path.isdir(source) and not os.listdir(source):
                os.rmdir(source)

    def test_provision_fails_when_database_already_exists(self):
        db_name = 'rcloud_prov_dup_%d' % os.getpid()
        provision_utils.create_database(db_name)
        try:
            tenant = self.env['rcloud.tenant'].create({
                'name': 'Dup Tenant', 'subdomain': 'duptest',
                'db_name': db_name, 'plan_id': self.plan.id,
            })
            job = self.env['rcloud.provision.job'].create({
                'tenant_id': tenant.id})
            job.action_run()
            self.assertEqual(job.state, 'failed')
            self.assertEqual(job.step, 'validate_subdomain')
        finally:
            provision_utils.drop_database(db_name)

    def test_provision_job_cannot_run_twice(self):
        tenant = self.env['rcloud.tenant'].create({
            'name': 'Done Tenant', 'subdomain': 'donetest',
            'db_name': 'rcloud_prov_done', 'plan_id': self.plan.id,
        })
        job = self.env['rcloud.provision.job'].create({
            'tenant_id': tenant.id})
        job.state = 'done'
        with self.assertRaises(ValueError):
            job.action_run()
