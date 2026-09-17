# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RcloudShareTransfer(models.Model):
    """Transfer of units between owners; the dated event that moves
    weighted positions once completed."""

    _name = 'rcloud.share.transfer'
    _description = 'Share Transfer'
    _order = 'transfer_date, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New',
        required=True)
    from_owner_id = fields.Many2one(
        'rcloud.owner', string='From Owner', required=True, index=True,
        ondelete='restrict')
    to_owner_id = fields.Many2one(
        'rcloud.owner', string='To Owner', required=True, index=True,
        ondelete='restrict')
    share_class_id = fields.Many2one(
        'rcloud.share.class', string='Share Class', required=True,
        ondelete='restrict')
    company_id = fields.Many2one(
        related='share_class_id.company_id', store=True, index=True,
        string='Company')
    units = fields.Integer(required=True)
    transfer_date = fields.Date(
        required=True, default=fields.Date.today, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)

    _units_positive = models.Constraint(
        'check(units > 0)', 'Transferred units must be positive.')

    @api.constrains('from_owner_id', 'to_owner_id')
    def _check_owners_differ(self):
        for t in self:
            if t.from_owner_id == t.to_owner_id:
                raise ValidationError(
                    _('A transfer needs two different owners.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rcloud.share.transfer') or 'New'
        return super().create(vals_list)

    # ---------------------------------------------------------- lifecycle
    def action_submit(self):
        for t in self:
            if t.state != 'draft':
                raise UserError(_('Only draft transfers can be submitted.'))
            t.state = 'submitted'
            t.message_post(body=_('Transfer submitted for approval.'))

    def action_approve(self):
        if not self.env.is_superuser() and not self.env.user.has_group(
                'rcloud_base.group_hotel_manager'):
            raise UserError(
                _('Only hotel managers can approve share transfers.'))
        for t in self:
            if t.state != 'submitted':
                raise UserError(_('Only submitted transfers can be approved.'))
            t.state = 'approved'
            t.message_post(body=_('Transfer approved.'))

    def action_reject(self):
        if not self.env.is_superuser() and not self.env.user.has_group(
                'rcloud_base.group_hotel_manager'):
            raise UserError(
                _('Only hotel managers can reject share transfers.'))
        for t in self:
            if t.state not in ('submitted', 'approved'):
                raise UserError(
                    _('Only submitted or approved transfers can be rejected.'))
            t.state = 'rejected'
            t.message_post(body=_('Transfer rejected.'))

    def action_complete(self):
        Holding = self.env['rcloud.share.holding'].sudo()
        for t in self:
            if t.state != 'approved':
                raise UserError(_('Only approved transfers can be completed.'))
            available = Holding.get_holding_on(
                t.from_owner_id, t.share_class_id, t.transfer_date)
            if available < t.units:
                raise UserError(_(
                    'The from-owner only holds %(avail).2f units of this '
                    'class on %(date)s; %(req)d were requested.') % {
                    'avail': available, 'date': t.transfer_date,
                    'req': t.units})
            t.state = 'completed'
            t.message_post(body=_(
                'Transfer of %(units)d units completed: %(from)s → %(to)s.') % {
                'units': t.units,
                'from': t.from_owner_id.partner_id.name,
                'to': t.to_owner_id.partner_id.name})
