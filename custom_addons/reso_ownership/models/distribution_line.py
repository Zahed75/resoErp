# -*- coding: utf-8 -*-
from odoo import fields, models


class ResoDistributionLine(models.Model):
    _name = 'reso.distribution.line'
    _description = 'Reso Distribution Line'
    _order = 'run_id, id'

    run_id = fields.Many2one(
        'reso.distribution.run', string='Distribution Run',
        required=True, ondelete='cascade', index=True)
    registry_id = fields.Many2one(
        'reso.owner.registry', string='Owner Registry', required=True,
        ondelete='restrict', index=True)
    partner_id = fields.Many2one(
        related='registry_id.partner_id', store=True, index=True,
        string='Owner')
    fraction_percent = fields.Float(
        related='registry_id.fraction_percent', store=True,
        string='Ownership (%)')
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='run_id.currency_id', store=True, string='Currency')
    company_id = fields.Many2one(
        related='run_id.company_id', store=True, index=True,
        string='Company')
    paid = fields.Boolean(string='Paid', default=False)
