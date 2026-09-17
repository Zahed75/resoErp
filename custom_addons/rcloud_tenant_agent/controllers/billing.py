# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class RcloudBillingController(http.Controller):

    def _billing_context(self):
        env = request.env
        ICP = env['ir.config_parameter'].sudo()
        Entitlement = env['rcloud_tenant_agent.entitlement'].sudo()
        state, grace_until = Entitlement.current_state()
        return {
            'state': state,
            'grace_until': grace_until or '',
            'tenant_id': ICP.get_param('rcloud.tenant_id', ''),
            'account_manager_name': ICP.get_param(
                'rcloud.account_manager_name', 'your account manager'),
            'account_manager_email': ICP.get_param(
                'rcloud.account_manager_email', ''),
            'account_manager_phone': ICP.get_param(
                'rcloud.account_manager_phone', ''),
            'entitlement_valid': Entitlement.verify(),
        }

    @http.route('/rcloud/billing', type='http', auth='public',
                methods=['GET'], csrf=False)
    def billing(self, **kwargs):
        """Reachable even while the tenant is suspended."""
        html = request.env['ir.qweb']._render(
            'rcloud_tenant_agent.billing_page', self._billing_context())
        return request.make_response(html)

    @http.route('/rcloud/billing/retry', type='http', auth='public',
                methods=['POST'], csrf=False)
    def retry(self, **kwargs):
        """Runs phone_home() once so a just-paid tenant unlocks without
        waiting for the next cron tick."""
        ok = request.env['rcloud_tenant_agent.agent'].sudo().phone_home()
        return request.make_response(
            json.dumps({'status': 'ok' if ok else 'unreachable'}),
            headers=[('Content-Type', 'application/json')],
            status=200 if ok else 503)
