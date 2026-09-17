# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudRatePlan(models.Model):
    _name = 'rcloud.rate.plan'
    _description = 'Rate Plan'
    _order = 'property_id, name'
    _inherit = 'rcloud.property.mixin'

    name = fields.Char(required=True)
    room_type_id = fields.Many2one(
        'rcloud.room.type', required=True, ondelete='restrict', index=True)
    channel = fields.Selection([
        ('direct', 'Direct'),
        ('ota', 'OTA'),
        ('corporate', 'Corporate'),
        ('walk_in', 'Walk-in'),
        ('agent', 'Travel Agent'),
    ], default='direct', required=True)
    cancellation_policy = fields.Selection([
        ('flexible', 'Flexible (24h)'),
        ('moderate', 'Moderate (48h, 1 night fee)'),
        ('strict', 'Strict (non-refundable)'),
    ], default='flexible', required=True)
    calendar_line_ids = fields.One2many(
        'rcloud.rate.calendar', 'rate_plan_id', string='Rate Calendar')

    _rate_name_uniq = models.Constraint(
        'unique(property_id, name)',
        'The rate plan name must be unique per property.')
