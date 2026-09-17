# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class RcloudFolio(models.Model):
    _name = 'rcloud.folio'
    _description = 'Guest Folio'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        readonly=True, copy=False, default='New',
        required=True, tracking=True)
    reservation_id = fields.Many2one(
        'rcloud.reservation', ondelete='set null', index=True)
    property_id = fields.Many2one(
        related='reservation_id.property_id', store=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Guest', required=True)
    company_id = fields.Many2one(
        related='reservation_id.company_id', store=True)
    currency_id = fields.Many2one(
        related='reservation_id.currency_id', store=True)
    line_ids = fields.One2many('rcloud.folio.line', 'folio_id',
                               string='Charges')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], default='open', required=True, tracking=True)
    balance = fields.Monetary(
        compute='_compute_balance', currency_field='currency_id',
        store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rcloud.folio') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_balance(self):
        for folio in self:
            folio.balance = sum(line.amount for line in folio.line_ids)

    def action_close(self):
        self.write({'state': 'closed'})


class RcloudFolioLine(models.Model):
    _name = 'rcloud.folio.line'
    _description = 'Folio Charge Line'

    folio_id = fields.Many2one(
        'rcloud.folio', required=True, ondelete='cascade', index=True)
    date = fields.Date(required=True, default=fields.Date.today)
    description = fields.Char(required=True)
    product_id = fields.Many2one('product.product', string='Item')
    qty = fields.Float(default=1.0, required=True)
    unit_price = fields.Monetary(required=True, currency_field='currency_id')
    amount = fields.Monetary(
        compute='_compute_amount', store=True, currency_field='currency_id')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    source = fields.Selection([
        ('room', 'Room'),
        ('pos', 'POS'),
        ('spa', 'Spa'),
        ('laundry', 'Laundry'),
        ('minibar', 'Minibar'),
        ('misc', 'Misc'),
    ], default='room', required=True)
    currency_id = fields.Many2one(
        related='folio_id.currency_id', store=True)

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty * line.unit_price
