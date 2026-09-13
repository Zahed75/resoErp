# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoRatePlan(models.Model):
    _name = 'reso.rate.plan'
    _description = 'Reso Rate Plan'
    _order = 'property_id, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Rate Plan', required=True, tracking=True)
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    room_type_id = fields.Many2one(
        'reso.room.type', string='Room Type', required=True,
        domain="[('property_id', '=', property_id)]")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id)
    base_price = fields.Monetary(string='Base Price', required=True,
                                 currency_field='currency_id')
    min_stay = fields.Integer(string='Min Stay', default=1)
    meal_plan = fields.Selection([
        ('none', 'Room Only'),
        ('breakfast', 'Breakfast'),
        ('half_board', 'Half Board'),
        ('full_board', 'Full Board'),
        ('all_inclusive', 'All Inclusive'),
    ], string='Meal Plan', default='none')
    cancellation_policy = fields.Selection([
        ('flexible', 'Flexible'),
        ('moderate', 'Moderate'),
        ('strict', 'Strict'),
        ('non_refundable', 'Non-Refundable'),
    ], string='Cancellation Policy', default='flexible')
    deposit_required = fields.Boolean(string='Deposit Required',
                                      default=False)
    deposit_percent = fields.Float(string='Deposit Percent', default=0.0)
    season_line_ids = fields.One2many('reso.rate.plan.season',
                                      'rate_plan_id', string='Seasons')
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')

    @api.constrains('property_id', 'room_type_id')
    def _check_room_type_property(self):
        for plan in self:
            if plan.room_type_id and plan.property_id and \
                    plan.room_type_id.property_id != plan.property_id:
                raise ValidationError(
                    _('The room type must belong to the same property '
                      'as the rate plan.'))

    @api.constrains('deposit_percent')
    def _check_deposit_percent(self):
        for plan in self:
            if not 0.0 <= plan.deposit_percent <= 100.0:
                raise ValidationError(
                    _('The deposit percent must be between 0 and 100.'))


class ResoRatePlanSeason(models.Model):
    _name = 'reso.rate.plan.season'
    _description = 'Reso Rate Plan Season'
    _order = 'date_from'

    rate_plan_id = fields.Many2one('reso.rate.plan',
                                   string='Rate Plan', required=True,
                                   ondelete='cascade')
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    price = fields.Monetary(string='Price', required=True,
                            currency_field='currency_id')
    currency_id = fields.Many2one(related='rate_plan_id.currency_id',
                                  store=True, string='Currency')
    company_id = fields.Many2one(related='rate_plan_id.company_id',
                                 store=True, index=True, string='Company')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for season in self:
            if season.date_from and season.date_to and \
                    season.date_to <= season.date_from:
                raise ValidationError(
                    _('The season end date must be after the start date.'))

    @api.constrains('rate_plan_id', 'date_from', 'date_to')
    def _check_overlap(self):
        for season in self:
            if not (season.date_from and season.date_to):
                continue
            overlap = self.search([
                ('id', '!=', season.id),
                ('rate_plan_id', '=', season.rate_plan_id.id),
                ('date_from', '<=', season.date_to),
                ('date_to', '>=', season.date_from),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    _('Season periods cannot overlap for the same '
                      'rate plan.'))
