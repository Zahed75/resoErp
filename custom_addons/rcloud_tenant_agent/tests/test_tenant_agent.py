# -*- coding: utf-8 -*-
import hmac as hmac_module
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestEntitlement(TransactionCase):

    def setUp(self):
        super().setUp()
        self.ICP = self.env['ir.config_parameter'].sudo()
        self.Entitlement = self.env['rcloud_tenant_agent.entitlement']
        self.ICP.set_param('rcloud.tenant_id', 'tenant-test-1')

    def test_sign_verify_round_trip(self):
        blob = self.Entitlement.sign(
            'active', '2026-12-31 00:00:00', 'tenant-test-1')
        self.ICP.set_param('rcloud.entitlement', blob)
        self.assertTrue(self.Entitlement.verify())
        self.assertEqual(
            self.Entitlement.current_state(),
            ('active', '2026-12-31 00:00:00'))

    def test_tamper_detection(self):
        blob = self.Entitlement.sign('active', None, 'tenant-test-1')
        payload, _, signature = blob.rpartition('.')
        forged = payload.replace('active', 'suspend') + '.' + signature
        self.ICP.set_param('rcloud.entitlement', forged)
        self.assertFalse(self.Entitlement.verify())
        # Corrupt signature is rejected too.
        self.ICP.set_param('rcloud.entitlement', payload + '.0' * 64)
        self.assertFalse(self.Entitlement.verify())

    def test_secret_is_database_uuid(self):
        uuid = self.ICP.get_param('database.uuid')
        blob = self.Entitlement.sign('trial', None, 'tenant-test-1')
        payload = blob.rpartition('.')[0]
        expected = hmac_module.new(
            uuid.encode(), payload.encode(), 'sha256').hexdigest()
        self.assertTrue(hmac_module.compare_digest(
            expected, blob.rpartition('.')[2]))


@tagged('post_install', '-at_install')
class TestLockGuard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.ICP = self.env['ir.config_parameter'].sudo()
        self.Entitlement = self.env['rcloud_tenant_agent.entitlement']
        self.ICP.set_param('rcloud.tenant_id', 'tenant-test-1')
        self.staff = self.env['res.users'].create({
            'name': 'Guard Staff', 'login': 'guard_staff',
            'group_ids': [(4, self.env.ref('base.group_user').id)],
        })

    def _suspend(self, grace_until):
        self.ICP.set_param(
            'rcloud.entitlement',
            self.Entitlement.sign('suspended', grace_until, 'tenant-test-1'))

    def test_blocked_when_suspended_and_grace_expired(self):
        past = (datetime.now() - timedelta(days=1)).strftime(
            '%Y-%m-%d %H:%M:%S')
        self._suspend(past)
        IrHttp = type(self.env['ir.http'])
        self.assertTrue(IrHttp._rcloud_blocked(
            '/web', self.staff, env=self.env))
        self.assertTrue(IrHttp._rcloud_blocked(
            '/odoo/action-123', self.staff, env=self.env))
        # Billing page, login and assets stay reachable.
        self.assertFalse(IrHttp._rcloud_blocked(
            '/rcloud/billing', self.staff, env=self.env))
        self.assertFalse(IrHttp._rcloud_blocked(
            '/web/login', self.staff, env=self.env))
        self.assertFalse(IrHttp._rcloud_blocked(
            '/web/assets/123/web.assets_web.min.js', self.staff,
            env=self.env))

    def test_not_blocked_within_grace(self):
        future = (datetime.now() + timedelta(days=3)).strftime(
            '%Y-%m-%d %H:%M:%S')
        self._suspend(future)
        IrHttp = type(self.env['ir.http'])
        self.assertFalse(IrHttp._rcloud_blocked(
            '/web', self.staff, env=self.env))

    def test_not_blocked_when_active(self):
        self.ICP.set_param(
            'rcloud.entitlement',
            self.Entitlement.sign('active', None, 'tenant-test-1'))
        IrHttp = type(self.env['ir.http'])
        self.assertFalse(IrHttp._rcloud_blocked(
            '/web', self.staff, env=self.env))

    def test_admin_never_blocked(self):
        past = (datetime.now() - timedelta(days=1)).strftime(
            '%Y-%m-%d %H:%M:%S')
        self._suspend(past)
        IrHttp = type(self.env['ir.http'])
        self.assertFalse(IrHttp._rcloud_blocked(
            '/web', self.env.user, env=self.env))

    def test_invalid_blob_means_open(self):
        self.ICP.set_param('rcloud.entitlement', 'garbage')
        IrHttp = type(self.env['ir.http'])
        self.assertFalse(IrHttp._rcloud_blocked(
            '/web', self.staff, env=self.env))


@tagged('post_install', '-at_install')
class TestPhoneHome(TransactionCase):

    def test_phone_home_success_updates_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('rcloud.control_plane_url', 'http://control.example')
        Entitlement = self.env['rcloud_tenant_agent.entitlement']
        new_blob = Entitlement.sign('active', None, 'tenant-x')
        payload = json.dumps({
            'rcloud.entitlement': new_blob,
            'rcloud.state': 'active',
            'rcloud.tenant_id': 'tenant-x',
        }).encode()
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.\
                return_value = payload
            ok = self.env['rcloud_tenant_agent.agent'].phone_home()
        self.assertTrue(ok)
        self.assertEqual(ICP.get_param('rcloud.state'), 'active')
        self.assertEqual(ICP.get_param('rcloud.tenant_id'), 'tenant-x')

    def test_phone_home_failure_keeps_cached_state(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('rcloud.control_plane_url', 'http://control.example')
        Entitlement = self.env['rcloud_tenant_agent.entitlement']
        blob = Entitlement.sign('suspended', '2020-01-01', 'tenant-x')
        ICP.set_param('rcloud.entitlement', blob)
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = OSError('unreachable')
            ok = self.env['rcloud_tenant_agent.agent'].phone_home()
        # Never self-unlock: the cached suspended blob survives.
        self.assertFalse(ok)
        self.assertEqual(
            ICP.get_param('rcloud.entitlement'), blob)
        self.assertEqual(
            Entitlement.current_state()[0], 'suspended')


@tagged('post_install', '-at_install')
class TestBillingPage(HttpCase):

    def test_billing_page_renders(self):
        response = self.url_open('/rcloud/billing')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Resort Cloud Billing', response.content)
