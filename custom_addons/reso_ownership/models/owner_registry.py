# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoOwnerRegistry(models.Model):
    _name = 'reso.owner.registry'
    _description = 'Reso Owner Registry'
    _order = 'property_id, certificate_number'
    _rec_name = 'certificate_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    certificate_number = fields.Char(
        string='Certificate No.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')
    partner_id = fields.Many2one(
        'res.partner', string='Owner', required=True)
    share_class = fields.Selection([
        ('fraction', 'Fractional Share'),
        ('whole', 'Whole Unit'),
        ('unit', 'Unit Count'),
    ], string='Share Class', required=True, default='fraction')
    fraction_percent = fields.Float(
        string='Ownership (%)', required=True, default=0.0)
    unit_count = fields.Float(string='Unit Count', default=0.0)
    date_acquired = fields.Date(
        string='Date Acquired', default=fields.Date.context_today)
    status = fields.Selection([
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('redeemed', 'Redeemed'),
    ], string='Status', default='active', tracking=True)
    acquisition_price = fields.Monetary(
        string='Acquisition Price', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True, string='Currency')
    note = fields.Text(string='Note')
    transfer_out_ids = fields.One2many(
        'reso.share.transfer', 'registry_id', string='Transfers Out',
        readonly=True)
    transfer_in_ids = fields.One2many(
        'reso.share.transfer', string='Transfers In', readonly=True,
        compute='_compute_transfer_in_ids')
    distribution_line_ids = fields.One2many(
        'reso.distribution.line', 'registry_id',
        string='Distribution Lines', readonly=True)

    _sql_constraints = [
        ('owner_share_class_uniq',
         'unique(property_id, partner_id, share_class)',
         'An owner can hold only one registry per share class '
         'on a property.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('certificate_number', _('New')) == _('New'):
                vals['certificate_number'] = self.env['ir.sequence']. \
                    next_by_code('reso.owner.registry') or _('New')
        return super().create(vals_list)

    @api.depends('partner_id.name', 'property_id.name', 'fraction_percent',
                 'share_class', 'certificate_number')
    def _compute_display_name(self):
        for registry in self:
            parts = []
            if registry.partner_id:
                parts.append(registry.partner_id.name)
            if registry.property_id:
                parts.append(registry.property_id.name)
            name = ' \u2014 '.join(parts) or registry.certificate_number
            if registry.share_class == 'fraction':
                name = '%s (%.2f%%)' % (name, registry.fraction_percent)
            registry.display_name = name

    @api.depends('partner_id', 'property_id')
    def _compute_transfer_in_ids(self):
        Transfer = self.env['reso.share.transfer']
        for registry in self:
            registry.transfer_in_ids = Transfer.search([
                ('registry_id.property_id', '=', registry.property_id.id),
                ('to_partner_id', '=', registry.partner_id.id),
            ])

    @api.constrains('fraction_percent', 'share_class', 'status')
    def _check_fraction_percent(self):
        for registry in self:
            if not 0.0 <= registry.fraction_percent <= 100.0:
                raise ValidationError(
                    _('Ownership (%) must be between 0 and 100.'))
            if registry.share_class == 'fraction' and \
                    registry.status == 'active' and \
                    registry.fraction_percent <= 0.0:
                raise ValidationError(
                    _('An active fractional holding must have an '
                      'Ownership (%) greater than 0.'))

    @api.constrains('fraction_percent', 'property_id', 'status',
                    'share_class')
    def _check_property_fraction_total(self):
        for registry in self:
            if registry.share_class != 'fraction' or \
                    registry.status != 'active':
                continue
            siblings = self.search([
                ('property_id', '=', registry.property_id.id),
                ('share_class', '=', 'fraction'),
                ('status', '=', 'active'),
            ])
            total = sum(siblings.mapped('fraction_percent'))
            if total > 100.0:
                raise ValidationError(
                    _('The total fractional ownership for property %s '
                      'cannot exceed 100%% (currently %.2f%%).')
                    % (registry.property_id.name, total))
