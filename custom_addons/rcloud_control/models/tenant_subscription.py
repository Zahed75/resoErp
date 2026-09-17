# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RcloudTenantSubscription(models.Model):
    """Billing subscription linking a tenant to a plan; the real invoice
    engine is sale.subscription."""

    _name = 'rcloud.tenant.subscription'
    _description = 'Tenant Subscription'
    _order = 'date_start desc, id desc'

    tenant_id = fields.Many2one(
        'rcloud.tenant', required=True, ondelete='cascade', index=True)
    plan_id = fields.Many2one(
        'rcloud.plan', required=True, ondelete='restrict')
    date_start = fields.Date(required=True, default=fields.Date.today)
    next_invoice_date = fields.Date()
    state = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ], default='active', required=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Subscription Order',
        help='The sale.order powering this subscription (Odoo 19 folds '
             'sale.subscription into sale.order).')
    mrr = fields.Monetary(
        compute='_compute_mrr', currency_field='currency_id', store=True)
    currency_id = fields.Many2one(
        related='plan_id.currency_id', store=True)

    @api.depends('plan_id.monthly_price', 'plan_id.billing_period')
    def _compute_mrr(self):
        for sub in self:
            price = sub.plan_id.monthly_price
            sub.mrr = price / 12.0 if sub.plan_id.billing_period == 'yearly' \
                else price
