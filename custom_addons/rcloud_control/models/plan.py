# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudPlan(models.Model):
    """A sellable subscription tier with hard resource limits."""

    _name = 'rcloud.plan'
    _description = 'Tenant Plan'
    _order = 'monthly_price'

    name = fields.Char(required=True)
    monthly_price = fields.Monetary(
        string='Monthly Price', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', required=True,
        default=lambda s: s.env.company.currency_id)
    billing_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], default='monthly', required=True)
    max_properties = fields.Integer(default=1)
    max_rooms = fields.Integer(default=20)
    max_users = fields.Integer(default=5)
    included_modules = fields.Char(
        help='Comma-separated module names included in this tier.')
    active = fields.Boolean(default=True)
