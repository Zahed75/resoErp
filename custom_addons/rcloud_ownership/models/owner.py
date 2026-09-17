# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudOwner(models.Model):
    """A fractional owner (shareholder) of one or more properties."""

    _name = 'rcloud.owner'
    _description = 'Owner'
    _order = 'id'
    _inherit = ['mail.thread']
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True, ondelete='restrict')
    kyc_state = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)
    bank_details = fields.Text(help='Bank name, account / IBAN for payouts.')
    tax_id = fields.Char(string='Tax ID')
    payout_preference = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ], default='bank_transfer', required=True)
    portal_user_id = fields.Many2one(
        'res.users', string='Portal User', ondelete='set null',
        domain="[('share', '=', True)]",
        help='Portal login through which the owner accesses /my/ownership.')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda s: s.env.company,
        ondelete='restrict', index=True)
    holding_ids = fields.One2many(
        'rcloud.share.holding', 'owner_id', string='Holdings')
    distribution_line_ids = fields.One2many(
        'rcloud.distribution.line', 'owner_id', string='Distribution Lines')

    _partner_uniq = models.Constraint(
        'unique(partner_id)',
        'One owner record per partner.')
