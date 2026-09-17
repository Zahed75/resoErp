# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

DISTRIBUTION_RULES = [
    ('gross_room_revenue', 'Gross Room Revenue'),
    ('noi', 'Net Operating Income'),
    ('room_subset', 'Room Subset'),
    ('guaranteed_or_share', 'Guaranteed or Share'),
]


class RcloudShareClass(models.Model):
    """A class of shares issued against a single property."""

    _name = 'rcloud.share.class'
    _description = 'Share Class'
    _order = 'property_id, name'
    _inherit = ['rcloud.property.mixin', 'mail.thread']
    _rec_name = 'name'

    name = fields.Char(required=True)
    total_units = fields.Integer(required=True, default=1)
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True)
    unit_nominal_value = fields.Monetary(
        currency_field='currency_id', required=True, default=0.0)
    distribution_rule = fields.Selection(
        DISTRIBUTION_RULES, required=True, default='gross_room_revenue',
        help='Basis on which distributions to this class are computed.')
    management_fee_pct = fields.Float(
        string='Management Fee %', default=0.0,
        help='Percentage deducted from the class allocation base.')
    reserve_pct = fields.Float(string='Reserve %', default=0.0)
    withholding_pct = fields.Float(string='Withholding %', default=0.0)
    room_type_ids = fields.Many2many(
        'rcloud.room.type', string='Room Types',
        help='Rooms counted for the "Room Subset" distribution rule.')
    expense_account_id = fields.Many2one(
        'account.account', string='Distribution Expense Account',
        help='Debit account for posted distribution entries; falls back '
             'to the first expense account of the company.')
    holding_ids = fields.One2many(
        'rcloud.share.holding', 'share_class_id', string='Holdings')

    @api.constrains('total_units')
    def _check_total_units(self):
        for cls in self:
            if cls.total_units <= 0:
                raise ValidationError(
                    _('Total units must be a positive number.'))

    @api.constrains('management_fee_pct', 'reserve_pct', 'withholding_pct')
    def _check_percentages(self):
        for cls in self:
            for pct in (cls.management_fee_pct, cls.reserve_pct,
                        cls.withholding_pct):
                if pct < 0 or pct > 100:
                    raise ValidationError(
                        _('Entitlement percentages must be between 0 and 100.'))

    @api.constrains('property_id', 'room_type_ids')
    def _check_room_types_property(self):
        for cls in self:
            for rt in cls.room_type_ids:
                if rt.property_id != cls.property_id:
                    raise ValidationError(
                        _('Room types must belong to the share class '
                          'property.'))

    def _deduction_rate(self):
        self.ensure_one()
        return (self.management_fee_pct + self.reserve_pct +
                self.withholding_pct) / 100.0

    def _expense_account(self):
        self.ensure_one()
        if self.expense_account_id:
            return self.expense_account_id
        return self.env['account.account'].sudo().search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', [self.company_id.id]),
        ], limit=1)
