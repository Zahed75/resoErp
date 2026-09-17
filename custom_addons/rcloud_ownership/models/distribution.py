# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .share_class import DISTRIBUTION_RULES


class RcloudDistributionRun(models.Model):
    """A period distribution run for one property.

    The manager inputs the distributable pool (total_amount); the engine
    pulls the revenue basis from posted accounting lines carrying the
    property's analytic account, applies per-share-class deductions and
    allocates the remainder to owners pro-rata on time-weighted units.
    """

    _name = 'rcloud.distribution.run'
    _description = 'Distribution Run'
    _order = 'period_start desc, id desc'
    _inherit = ['rcloud.property.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New',
        required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    revenue_basis = fields.Selection(
        DISTRIBUTION_RULES, required=True, default='gross_room_revenue')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
    ], default='draft', required=True, tracking=True)
    total_amount = fields.Monetary(
        string='Distributable Pool', currency_field='currency_id',
        help='Pool allocated to owners, entered by the manager.')
    basis_amount = fields.Monetary(
        string='Computed Basis', currency_field='currency_id', readonly=True,
        help='Revenue basis pulled from posted accounting analytic lines.')
    deduction_amount = fields.Monetary(
        compute='_compute_amounts', currency_field='currency_id')
    distributable_amount = fields.Monetary(
        compute='_compute_amounts', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True)
    line_ids = fields.One2many(
        'rcloud.distribution.line', 'run_id', string='Distribution Lines')

    _period_valid = models.Constraint(
        'check(period_end > period_start)',
        'The period end must be after the period start.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rcloud.distribution.run') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.deductions', 'line_ids.net_payable',
                 'total_amount')
    def _compute_amounts(self):
        for run in self:
            run.deduction_amount = sum(
                line.deductions for line in run.line_ids)
            run.distributable_amount = run.total_amount - run.deduction_amount

    # -------------------------------------------------------- accounting
    def _compute_basis_amount(self):
        """Sum of posted journal item balances on the property's analytic
        account within the period. Income accounts for gross bases; NOI
        additionally subtracts expense-group lines."""
        self.ensure_one()
        analytic = self.property_id.analytic_account_id
        if not analytic:
            return 0.0
        Line = self.env['account.move.line'].sudo()
        domain = [
            ('analytic_distribution', 'in', [str(analytic.id)]),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
        ]
        income = -sum(r['balance'] for r in Line.search_read(
            domain + [('account_id.internal_group', '=', 'income')],
            ['balance']))
        if self.revenue_basis != 'noi':
            return income
        expense = sum(r['balance'] for r in Line.search_read(
            domain + [('account_id.internal_group', '=', 'expense')],
            ['balance']))
        return income - expense

    # ---------------------------------------------------------- lifecycle
    def action_calculate(self):
        """(Re)compute lines. Only draft/computed runs are mutable."""
        Holding = self.env['rcloud.share.holding'].sudo()
        for run in self:
            if run.state not in ('draft', 'computed'):
                raise UserError(_(
                    'Only draft or computed runs can be recalculated.'))
            run.line_ids.sudo().unlink()
            run.basis_amount = run._compute_basis_amount()
            if not run.total_amount:
                run.total_amount = run.basis_amount
            run._allocate_lines(Holding)
            run.state = 'computed'
            run.message_post(body=_(
                'Distribution calculated: %(lines)d lines, %(net)s net.') % {
                'lines': len(run.line_ids),
                'net': run.distributable_amount})

    def _allocate_lines(self, Holding):
        self.ensure_one()
        rounder = self.currency_id.round
        classes = self.env['rcloud.share.class'].sudo().search([
            ('property_id', '=', self.property_id.id)])
        if not classes:
            raise UserError(_('This property has no share classes.'))
        # (owner, class) -> full-precision allocation dicts
        Transfer = self.env['rcloud.share.transfer'].sudo()
        per_class = {}
        for cls in classes:
            candidates = Holding.search([
                ('share_class_id', '=', cls.id),
                ('state', '=', 'active')]).mapped('owner_id')
            transfers = Transfer.search([
                ('share_class_id', '=', cls.id),
                ('state', '=', 'completed')])
            candidates |= transfers.from_owner_id | transfers.to_owner_id
            owners = {}
            for owner in candidates:
                weighted = Holding.get_weighted_units(
                    owner, cls, self.period_start, self.period_end)
                if weighted > 0:
                    owners[owner] = weighted
            if owners:
                per_class[cls] = owners
        total_weighted = sum(sum(o.values()) for o in per_class.values())
        if total_weighted <= 0:
            raise UserError(_(
                'No weighted units held during the period.'))
        lines = []
        for cls, owners in per_class.items():
            class_base = self.total_amount * \
                sum(owners.values()) / total_weighted
            deductions_full = class_base * cls._deduction_rate()
            distributable = class_base - deductions_full
            for owner, weighted in owners.items():
                share = weighted / sum(owners.values())
                lines.append({
                    'owner_id': owner.id,
                    'share_class_id': cls.id,
                    'units_held': weighted,
                    'share_pct': share * 100.0,
                    'gross_allocated': rounder(class_base * share),
                    'deductions': rounder(deductions_full * share),
                    'net_payable': rounder(distributable * share),
                })
        # Cent-exact rounding: force the sum of net_payable to equal the
        # distributable amount exactly by parking the residual on the
        # largest line.
        distributable_total = rounder(self.total_amount) - sum(
            l['deductions'] for l in lines)
        residual = rounder(distributable_total - sum(
            l['net_payable'] for l in lines))
        if lines and residual:
            largest = max(lines, key=lambda l: l['net_payable'])
            largest['net_payable'] = rounder(
                largest['net_payable'] + residual)
        self.env['rcloud.distribution.line'].sudo().create([
            dict(line, run_id=self.id) for line in lines])

    def action_approve(self):
        if not self.env.is_superuser() and not self.env.user.has_group(
                'rcloud_base.group_hotel_manager'):
            raise UserError(
                _('Only hotel managers can approve distribution runs.'))
        for run in self:
            if run.state != 'computed':
                raise UserError(_('Only computed runs can be approved.'))
            run.state = 'approved'
            run.message_post(body=_('Distribution approved.'))

    def action_post(self):
        """Post one journal entry per line:
        debit distribution expense, credit partner payable."""
        Move = self.env['account.move'].sudo()
        for run in self:
            if run.state != 'approved':
                raise UserError(_('Only approved runs can be posted.'))
            if not run.line_ids:
                raise UserError(_('Nothing to post: run has no lines.'))
            journal = run._general_journal()
            payable = run._payable_account()
            for line in run.line_ids:
                expense = line.share_class_id._expense_account()
                if not expense:
                    raise UserError(_(
                        'No expense account configured for share class '
                        '"%s" and none found on the company.') %
                        line.share_class_id.name)
                if not payable:
                    raise UserError(_(
                        'No payable account found for company %s.') %
                        run.company_id.name)
                move = Move.create({
                    'move_type': 'entry',
                    'journal_id': journal.id,
                    'date': fields.Date.today(),
                    'ref': '%s / %s' % (run.name, line.owner_id.partner_id.name),
                    'line_ids': [
                        (0, 0, {
                            'name': run.name,
                            'account_id': expense.id,
                            'debit': line.net_payable,
                            'credit': 0.0,
                        }),
                        (0, 0, {
                            'name': run.name,
                            'account_id': payable.id,
                            'partner_id': line.owner_id.partner_id.id,
                            'debit': 0.0,
                            'credit': line.net_payable,
                        }),
                    ],
                })
                move.action_post()
                line.move_id = move
            run.state = 'posted'
            run.message_post(body=_(
                'Distribution posted: %(count)d journal entries.') % {
                'count': len(run.line_ids)})

    def action_mark_paid(self):
        Payment = self.env['account.payment'].sudo()
        for run in self:
            if run.state != 'posted':
                raise UserError(_('Only posted runs can be marked paid.'))
            journal = run._bank_journal()
            if not journal:
                raise UserError(_(
                    'No bank or cash journal found for company %s.') %
                    run.company_id.name)
            for line in run.line_ids:
                payment = Payment.create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': line.owner_id.partner_id.id,
                    'amount': line.net_payable,
                    'journal_id': journal.id,
                    'date': fields.Date.today(),
                    'payment_reference': run.name,
                })
                line.payment_id = payment
                line.state = 'paid'
            run.state = 'paid'
            run.message_post(body=_(
                'Distribution marked paid: %(count)d payments.') % {
                'count': len(run.line_ids)})

    def _general_journal(self):
        self.ensure_one()
        return self.env['account.journal'].sudo().search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    def _bank_journal(self):
        self.ensure_one()
        return self.env['account.journal'].sudo().search([
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    def _payable_account(self):
        self.ensure_one()
        return self.env['account.account'].sudo().search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', [self.company_id.id]),
        ], limit=1)


class RcloudDistributionLine(models.Model):
    _name = 'rcloud.distribution.line'
    _description = 'Distribution Line'
    _order = 'run_id, id'

    run_id = fields.Many2one(
        'rcloud.distribution.run', required=True, ondelete='cascade',
        index=True)
    owner_id = fields.Many2one(
        'rcloud.owner', required=True, ondelete='restrict', index=True)
    share_class_id = fields.Many2one(
        'rcloud.share.class', required=True, ondelete='restrict')
    property_id = fields.Many2one(
        related='run_id.property_id', store=True, index=True)
    company_id = fields.Many2one(
        related='run_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(
        related='run_id.currency_id', store=True)
    units_held = fields.Float(
        string='Weighted Units', digits=(16, 2),
        help='Time-weighted units held during the run period.')
    share_pct = fields.Float(string='Share %', digits=(16, 4))
    gross_allocated = fields.Monetary(currency_field='currency_id')
    deductions = fields.Monetary(currency_field='currency_id')
    net_payable = fields.Monetary(currency_field='currency_id')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], default='pending', required=True)
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True, copy=False)
    payment_id = fields.Many2one(
        'account.payment', string='Payment', readonly=True, copy=False)

    @api.constrains('gross_allocated', 'deductions', 'net_payable')
    def _check_amounts(self):
        for line in self:
            for amount in (line.gross_allocated, line.deductions,
                           line.net_payable):
                if amount < 0:
                    raise ValidationError(
                        _('Distribution amounts cannot be negative.'))
