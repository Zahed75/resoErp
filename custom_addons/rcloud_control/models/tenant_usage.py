# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudTenantUsage(models.Model):
    """Daily snapshot of a tenant's resource consumption."""

    _name = 'rcloud.tenant.usage'
    _description = 'Tenant Usage Snapshot'
    _order = 'date desc, id desc'

    tenant_id = fields.Many2one(
        'rcloud.tenant', required=True, ondelete='cascade', index=True)
    date = fields.Date(required=True, default=fields.Date.today)
    rooms = fields.Integer()
    users = fields.Integer()
    reservations = fields.Integer()
    storage_mb = fields.Integer(string='Storage (MB)')

    _tenant_date_uniq = models.Constraint(
        'unique(tenant_id, date)',
        'A tenant can only have one usage snapshot per day.')
