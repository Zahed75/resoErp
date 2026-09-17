# -*- coding: utf-8 -*-
import json
import logging
import urllib.request

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RcloudTenantAgent(models.Model):
    """Phones home to the control plane on a cron and refreshes the
    cached signed entitlement. A failed call keeps the cached state —
    the tenant never upgrades itself."""

    _name = 'rcloud_tenant_agent.agent'
    _description = 'Tenant Agent'

    name = fields.Char(default='Tenant Agent', required=True)

    @api.model
    def phone_home(self):
        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param('rcloud.control_plane_url')
        if not url:
            _logger.info('rcloud: no control plane URL configured, '
                         'keeping cached entitlement')
            return False
        Entitlement = self.env['rcloud_tenant_agent.entitlement']
        state, grace_until = Entitlement.current_state()
        payload = {
            'tenant_id': ICP.get_param(
                Entitlement.PARAM_TENANT_ID, ''),
            'state': state,
            'grace_until': grace_until,
            'entitlement': ICP.get_param(
                Entitlement.PARAM_ENTITLEMENT, ''),
            'db': self.env.cr.dbname,
        }
        try:
            req = urllib.request.Request(
                url.rstrip('/') + '/api/entitlement',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST')
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            _logger.warning(
                'rcloud: phone-home failed (%s), keeping cached state',
                exc)
            return False
        if not isinstance(result, dict):
            return False
        for key in ('rcloud.entitlement', 'rcloud.state',
                    'rcloud.grace_until', 'rcloud.tenant_id'):
            if result.get(key):
                ICP.set_param(key, result[key])
        return True
