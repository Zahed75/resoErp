# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoRoom(models.Model):
    _name = 'reso.room'
    _description = 'Reso Room'
    _order = 'property_id, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Room / Villa No.', required=True)
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    room_type_id = fields.Many2one(
        'reso.room.type', string='Room Type', required=True,
        domain="[('property_id', '=', property_id)]")
    floor = fields.Char(string='Floor')
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning / Dirty'),
        ('inspecting', 'Inspecting'),
        ('maintenance', 'Maintenance'),
        ('out_of_order', 'Out of Order'),
    ], string='Occupancy Status', default='available', tracking=True)
    housekeeping_status = fields.Selection([
        ('clean', 'Clean'),
        ('dirty', 'Dirty'),
        ('inspecting', 'Inspecting'),
        ('in_progress', 'Cleaning in Progress'),
    ], string='Housekeeping Status', default='clean', tracking=True)
    housekeeper_id = fields.Many2one('res.users', string='Assigned Housekeeper', tracking=True)
    last_cleaned = fields.Datetime(string='Last Cleaned')
    notes = fields.Text(string='Notes / Instructions')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')

    _sql_constraints = [
        ('property_room_uniq', 'unique(property_id, name)',
         'A room with this number already exists for this property.'),
    ]

    @api.constrains('property_id', 'room_type_id')
    def _check_room_type_property(self):
        for room in self:
            if room.room_type_id and room.property_id and \
                    room.room_type_id.property_id != room.property_id:
                raise ValidationError(
                    _('The room type must belong to the same property '
                      'as the room.'))

    def action_mark_clean(self):
        for room in self:
            room.write({
                'housekeeping_status': 'clean',
                'last_cleaned': fields.Datetime.now(),
            })
            if room.status == 'cleaning':
                room.status = 'available'

    def action_mark_dirty(self):
        for room in self:
            room.write({
                'housekeeping_status': 'dirty',
            })
            if room.status == 'available':
                room.status = 'cleaning'

    def action_mark_inspecting(self):
        for room in self:
            room.write({
                'housekeeping_status': 'inspecting',
            })

    def action_mark_in_progress(self):
        for room in self:
            room.write({
                'housekeeping_status': 'in_progress',
            })
