# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RcloudRateCalendar(models.Model):
    """One row per rate plan per date: rate, min-stay, closed to arrival."""

    _name = 'rcloud.rate.calendar'
    _description = 'Rate Calendar'
    _order = 'date'

    rate_plan_id = fields.Many2one(
        'rcloud.rate.plan', required=True, ondelete='cascade', index=True)
    property_id = fields.Many2one(
        related='rate_plan_id.property_id', store=True, index=True)
    date = fields.Date(required=True, index=True)
    rate = fields.Monetary(required=True, currency_field='currency_id')
    min_stay = fields.Integer(default=1)
    closed_to_arrival = fields.Boolean(default=False)
    currency_id = fields.Many2one(
        related='rate_plan_id.property_id.currency_id', store=True)

    _rate_day_uniq = models.Constraint(
        'unique(rate_plan_id, date)',
        'A rate plan can only have one calendar row per date.')

    @api.constrains('rate', 'min_stay')
    def _check_values(self):
        for row in self:
            if row.rate < 0:
                raise ValidationError(_('Rate cannot be negative.'))
            if row.min_stay < 1:
                raise ValidationError(_('Min stay must be at least 1.'))

    @api.model
    def rate_for(self, rate_plan, date):
        row = self.search([
            ('rate_plan_id', '=', rate_plan.id),
            ('date', '=', date),
        ], limit=1)
        if row:
            return row.rate, row.min_stay, row.closed_to_arrival
        return rate_plan.room_type_id.default_rate, 1, False
