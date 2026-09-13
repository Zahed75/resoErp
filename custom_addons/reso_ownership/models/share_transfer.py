# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class ResoShareTransfer(models.Model):
    _name = 'reso.share.transfer'
    _description = 'Reso Share Transfer'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Transfer No.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    registry_id = fields.Many2one(
        'reso.owner.registry', string='Source Registry', required=True,
        ondelete='restrict',
        domain="[('status', '=', 'active')]")
    property_id = fields.Many2one(
        related='registry_id.property_id', store=True, index=True,
        string='Property')
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')
    from_partner_id = fields.Many2one(
        related='registry_id.partner_id', store=True, string='From Owner')
    to_partner_id = fields.Many2one(
        'res.partner', string='To Owner', required=True)
    fraction_percent = fields.Float(
        string='Ownership (%)', required=True, default=0.0)
    transfer_date = fields.Date(
        string='Transfer Date', default=fields.Date.context_today)
    consideration_amount = fields.Monetary(
        string='Consideration', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='registry_id.currency_id', store=True, string='Currency')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', readonly=True, copy=False,
        tracking=True)
    submitted_by = fields.Many2one(
        'res.users', string='Submitted By', default=lambda self: self.env.uid)
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False)
    approval_date = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Text(copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence']. \
                    next_by_code('reso.share.transfer') or _('New')
        return super().create(vals_list)

    @api.constrains('to_partner_id', 'from_partner_id')
    def _check_partners(self):
        for transfer in self:
            if transfer.to_partner_id and transfer.from_partner_id and \
                    transfer.to_partner_id == transfer.from_partner_id:
                raise ValidationError(
                    _('Cannot transfer ownership to the same owner.'))

    @api.constrains('fraction_percent')
    def _check_fraction_percent(self):
        for transfer in self:
            if transfer.fraction_percent <= 0.0:
                raise ValidationError(
                    _('The transferred Ownership (%) must be positive.'))

    def action_submit(self):
        for transfer in self:
            if transfer.state != 'draft':
                raise UserError(
                    _('Only draft transfers can be submitted.'))
            transfer.write({'state': 'submitted'})

    def action_approve(self):
        if not self.env.user.has_group(
                'reso_ownership.group_ownership_manager'):
            raise UserError(
                _('Only an Ownership Manager can approve transfers.'))
        for transfer in self:
            if transfer.state != 'submitted':
                raise UserError(
                    _('Only submitted transfers can be approved.'))
            transfer.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approval_date': fields.Datetime.now(),
            })

    def action_reject(self):
        for transfer in self:
            if transfer.state != 'submitted':
                raise UserError(
                    _('Only submitted transfers can be rejected.'))
            if not transfer.rejection_reason:
                raise UserError(
                    _('Please provide a rejection reason.'))
            transfer.write({'state': 'rejected'})

    def action_complete(self):
        Registry = self.env['reso.owner.registry']
        for transfer in self:
            if transfer.state != 'approved':
                raise UserError(
                    _('Only approved transfers can be completed.'))
            registry = transfer.registry_id
            if float_compare(transfer.fraction_percent,
                             registry.fraction_percent,
                             precision_rounding=0.00001) == 1:
                raise UserError(
                    _('The transferred Ownership (%%) (%.2f) exceeds the '
                      'remaining fraction of %s (%.2f%%).')
                    % (transfer.fraction_percent,
                       registry.partner_id.name,
                       registry.fraction_percent))
            new_fraction = registry.fraction_percent - \
                transfer.fraction_percent
            # Reduce the source holding first: creating the target
            # holding while the source still holds its full fraction
            # would trip the 100% property-wide cap.
            if float_compare(new_fraction, 0.0,
                             precision_rounding=0.00001) <= 0:
                registry.write({
                    'fraction_percent': 0.0,
                    'status': 'redeemed',
                })
            else:
                registry.write({'fraction_percent': new_fraction})
            Registry.create({
                'property_id': registry.property_id.id,
                'partner_id': transfer.to_partner_id.id,
                'share_class': registry.share_class,
                'fraction_percent': transfer.fraction_percent,
                'unit_count': registry.unit_count
                if registry.share_class == 'unit' else 0.0,
                'date_acquired': transfer.transfer_date,
                'acquisition_price': transfer.consideration_amount,
                'note': _('Transferred from %s via %s')
                        % (registry.partner_id.name, transfer.name),
            })
            transfer.write({'state': 'completed'})
