# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class RcloudProperty(models.Model):
    """A bookable property (resort/hotel branch). Every operational and
    financial record in the product carries this dimension."""

    _name = 'rcloud.property'
    _description = 'Property'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, help='Short unique code, e.g. CBB')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda s: s.env.company,
        ondelete='restrict', index=True)
    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    country_id = fields.Many2one('res.country')
    phone = fields.Char()
    email = fields.Char()
    timezone = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['tz'].selection,
        default='UTC')
    currency_id = fields.Many2one(
        'res.currency', required=True,
        default=lambda s: s.env.company.currency_id)
    checkin_time = fields.Float(default=14.0)
    checkout_time = fields.Float(default=12.0)
    tax_ids = fields.Many2many(
        'account.tax', string='Default Taxes',
        domain="[('type_tax_use', '=', 'sale')]",
        help='Configuration-driven default sale taxes for this property.')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', readonly=True, copy=False,
        help='Auto-created under the "Property" analytic plan.')
    total_rooms = fields.Integer(
        compute='_compute_total_rooms', store=True)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique(code, company_id)',
        'The property code must be unique per company.')

    @api.depends('company_id')
    def _compute_total_rooms(self):
        for prop in self:
            if 'rcloud.room' not in self.env:
                prop.total_rooms = 0
                continue
            rooms = self.env['rcloud.room'].sudo().search_count(
                [('property_id', '=', prop.id)])
            prop.total_rooms = rooms

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_analytic_accounts()
        return records

    def _ensure_analytic_accounts(self):
        """One analytic account per property under the Property plan —
        the backbone of per-property reporting."""
        plan = self.env.ref('rcloud_base.property_analytic_plan',
                            raise_if_not_found=False)
        if not plan:
            plan = self.env['account.analytic.plan'].sudo().create({
                'name': 'Property',
                'default_applicability': 'optional',
            })
            self.env['ir.model.data'].sudo().create({
                'module': 'rcloud_base', 'name': 'property_analytic_plan',
                'model': 'account.analytic.plan', 'res_id': plan.id,
                'noupdate': True,
            })
        Analytic = self.env['account.analytic.account'].sudo()
        for prop in self:
            if not prop.analytic_account_id:
                prop.analytic_account_id = Analytic.create({
                    'name': prop.name,
                    'plan_id': plan.id,
                    'company_id': prop.company_id.id,
                }).id

    def action_view_rooms(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rooms'),
            'res_model': 'rcloud.room',
            'domain': [('property_id', '=', self.id)],
            'views': [[False, 'list'], [False, 'form']],
        }
