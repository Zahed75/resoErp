# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class RcloudImpersonationLog(models.Model):
    """Audit trail of support impersonation sessions. Immutable: records
    can be created and closed, never edited or deleted."""

    _name = 'rcloud.impersonation.log'
    _description = 'Impersonation Log'
    _order = 'id desc'

    admin_user_id = fields.Many2one(
        'res.users', string='Support User', required=True,
        ondelete='restrict')
    tenant_id = fields.Many2one(
        'rcloud.tenant', required=True, ondelete='restrict')
    started_on = fields.Datetime(required=True, default=fields.Datetime.now)
    ended_on = fields.Datetime()
    note = fields.Char()

    def write(self, vals):
        if 'ended_on' in vals and any(log.ended_on for log in self):
            raise UserError(_(
                'Impersonation log entries cannot be modified once closed.'))
        return super().write(vals)

    def unlink(self):
        raise UserError(_(
            'Impersonation log entries are immutable and cannot be '
            'deleted.'))
