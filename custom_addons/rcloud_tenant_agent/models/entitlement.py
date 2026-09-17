# -*- coding: utf-8 -*-
import hashlib
import hmac as hmac_module

from odoo import models


class RcloudTenantAgentEntitlement(models.AbstractModel):
    """Signed entitlement blob, cached per database.

    Payload format: 'state|grace_until|tenant_id' signed with HMAC-SHA256
    keyed on the tenant's own database uuid. The control plane holds the
    matching copy; the tenant can verify but never forge or extend it.
    """

    _name = 'rcloud_tenant_agent.entitlement'
    _description = 'Tenant Entitlement Helper'

    PARAM_ENTITLEMENT = 'rcloud.entitlement'
    PARAM_STATE = 'rcloud.state'
    PARAM_GRACE = 'rcloud.grace_until'
    PARAM_TENANT_ID = 'rcloud.tenant_id'

    def _secret(self):
        return (self.env['ir.config_parameter'].sudo().get_param(
            'database.uuid') or '').encode('utf-8')

    def _payload(self, state, grace_until, tenant_id):
        return '%s|%s|%s' % (state, grace_until or '', tenant_id or '')

    def _sign_payload(self, payload):
        return hmac_module.new(
            self._secret(), payload.encode('utf-8'),
            hashlib.sha256).hexdigest()

    def sign(self, state, grace_until=None, tenant_id=None):
        """Return 'payload_hexsignature' for the given values."""
        ICP = self.env['ir.config_parameter'].sudo()
        if tenant_id is None:
            tenant_id = ICP.get_param(self.PARAM_TENANT_ID, '')
        payload = self._payload(state, grace_until, tenant_id)
        return '%s.%s' % (payload, self._sign_payload(payload))

    def verify(self):
        """Check the cached blob against its signature and the current
        tenant secret. Returns True only when intact."""
        ICP = self.env['ir.config_parameter'].sudo()
        blob = ICP.get_param(self.PARAM_ENTITLEMENT, '')
        if not blob or '.' not in blob:
            return False
        payload, _, signature = blob.rpartition('.')
        tenant_id = ICP.get_param(self.PARAM_TENANT_ID, '')
        expected = self._payload(*self._parse_payload(payload, tenant_id))
        return hmac_module.compare_digest(
            signature, self._sign_payload(expected))

    def _parse_payload(self, payload, fallback_tenant_id):
        parts = payload.split('|')
        parts += [''] * (3 - len(parts))
        state, grace_until, tenant_id = parts[:3]
        return state, grace_until, tenant_id or fallback_tenant_id

    def current_state(self):
        """(state, grace_until) as cached, or ('active', None) when no
        valid entitlement exists (fresh installs stay open)."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not self.verify():
            return 'active', None
        blob = ICP.get_param(self.PARAM_ENTITLEMENT, '')
        payload = blob.rpartition('.')[0]
        state, grace_until, _tenant = self._parse_payload(
            payload, ICP.get_param(self.PARAM_TENANT_ID, ''))
        return state, grace_until or None
