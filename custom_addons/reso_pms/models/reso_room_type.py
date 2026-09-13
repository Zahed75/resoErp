# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoRoomType(models.Model):
    _name = 'reso.room.type'
    _description = 'Reso Room Type'
    _order = 'property_id, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Room Type', required=True, tracking=True)
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    code = fields.Char(string='Code')
    max_guests = fields.Integer(string='Max Guests', required=True,
                                default=2)
    bed_type = fields.Selection([
        ('single', 'Single'),
        ('twin', 'Twin'),
        ('double', 'Double'),
        ('queen', 'Queen'),
        ('king', 'King'),
        ('bunk', 'Bunk Bed'),
        ('sofa', 'Sofa Bed'),
    ], string='Bed Type', default='double')
    amenity_ids = fields.Many2many(
        'reso.room.amenity', string='Amenities')
    description = fields.Text(string='Description')
    image_1920 = fields.Image(string='Image')
    room_ids = fields.One2many('reso.room', 'room_type_id',
                               string='Rooms')
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')

    @api.constrains('max_guests')
    def _check_max_guests(self):
        for room_type in self:
            if room_type.max_guests <= 0:
                raise ValidationError(
                    _('The maximum number of guests must be positive.'))
