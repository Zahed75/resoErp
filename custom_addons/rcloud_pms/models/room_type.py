# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RcloudRoomAmenity(models.Model):
    _name = 'rcloud.room.amenity'
    _description = 'Room Amenity'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class RcloudRoomType(models.Model):
    _name = 'rcloud.room.type'
    _description = 'Room Type'
    _order = 'property_id, name'
    _inherit = ['rcloud.property.mixin', 'mail.thread']

    name = fields.Char(required=True)
    code = fields.Char()
    base_occupancy = fields.Integer(default=2, required=True)
    max_occupancy = fields.Integer(default=2, required=True)
    amenity_ids = fields.Many2many('rcloud.room.amenity', string='Amenities')
    default_rate = fields.Monetary(
        currency_field='currency_id', required=True, default=0.0)
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True)
    room_ids = fields.One2many('rcloud.room', 'room_type_id', string='Rooms')
    room_count = fields.Integer(compute='_compute_room_count', store=True)

    _type_code_uniq = models.Constraint(
        'unique(property_id, code)',
        'The room type code must be unique per property.')

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rt in self:
            rt.room_count = len(rt.room_ids)

    def _sync_availability_totals(self):
        Availability = self.env['rcloud.availability'].sudo()
        for rt in self:
            buckets = Availability.search([('room_type_id', '=', rt.id)])
            if buckets:
                buckets.write({'total': rt.room_count})
