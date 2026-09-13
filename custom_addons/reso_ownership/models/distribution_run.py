# -*- coding: utf-8 -*-
from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round


class ResoDistributionRun(models.Model):
    _name = 'reso.distribution.run'
    _description = 'Reso Distribution Run'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Distribution No.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True, string='Currency')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    total_amount = fields.Monetary(
        string='Pool Amount', required=True, currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', readonly=True, copy=False,
        tracking=True)
    line_ids = fields.One2many(
        'reso.distribution.line', 'run_id', string='Distribution Lines',
        readonly=True)
    calculated_by = fields.Many2one(
        'res.users', string='Calculated By', readonly=True, copy=False)
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False)
    line_count = fields.Integer(
        string='Number of Lines', compute='_compute_totals')
    total_distributed = fields.Monetary(
        string='Distributed', compute='_compute_totals',
        currency_field='currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence']. \
                    next_by_code('reso.distribution.run') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_totals(self):
        for run in self:
            run.line_count = len(run.line_ids)
            run.total_distributed = sum(run.line_ids.mapped('amount'))

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for run in self:
            if run.period_start and run.period_end and \
                    run.period_end <= run.period_start:
                raise ValidationError(
                    _('The distribution period end must be after '
                      'the period start.'))

    def action_calculate(self):
        Registry = self.env['reso.owner.registry']
        for run in self:
            if run.state != 'draft':
                raise UserError(
                    _('Only draft distribution runs can be calculated.'))
            run.line_ids.unlink()
            rounding = run.currency_id.rounding or 0.01
            registries = Registry.search([
                ('property_id', '=', run.property_id.id),
                ('share_class', '=', 'fraction'),
                ('status', '=', 'active'),
                ('fraction_percent', '>', 0.0),
            ])
            amounts = {}
            for registry in registries:
                amounts[registry.id] = float_round(
                    run.total_amount * registry.fraction_percent / 100.0,
                    precision_rounding=rounding)
            residual = float_round(
                run.total_amount - sum(amounts.values()),
                precision_rounding=rounding)
            if amounts and float_compare(residual, 0.0,
                                         precision_rounding=rounding) != 0:
                largest_registry_id = max(amounts, key=lambda rid: amounts[rid])
                amounts[largest_registry_id] = float_round(
                    amounts[largest_registry_id] + residual,
                    precision_rounding=rounding)
            run.write({
                'state': 'calculated',
                'calculated_by': self.env.uid,
                'line_ids': [
                    Command.create({
                        'registry_id': registry.id,
                        'amount': amounts[registry.id],
                    }) for registry in registries
                ],
            })

    def action_view_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Distribution Lines'),
            'res_model': 'reso.distribution.line',
            'view_mode': 'list,form',
            'domain': [('run_id', '=', self.id)],
            'context': {'default_run_id': self.id},
        }

    def action_approve(self):
        if not self.env.user.has_group(
                'reso_ownership.group_ownership_manager'):
            raise UserError(
                _('Only an Ownership Manager can approve distribution '
                  'runs.'))
        for run in self:
            if run.state != 'calculated':
                raise UserError(
                    _('Only calculated distribution runs can be '
                      'approved.'))
            run.write({
                'state': 'approved',
                'approved_by': self.env.uid,
            })

    def action_mark_paid(self):
        for run in self:
            if run.state != 'approved':
                raise UserError(
                    _('Only approved distribution runs can be marked '
                      'as paid.'))
            run.write({'state': 'paid'})
            run.line_ids.write({'paid': True})

    def action_reset(self):
        for run in self:
            if run.state != 'calculated':
                raise UserError(
                    _('Only calculated distribution runs can be reset.'))
            run.write({
                'state': 'draft',
                'calculated_by': False,
                'line_ids': [Command.clear()],
            })
