# -*- coding: utf-8 -*-
from odoo import fields, models


class ResoProperty(models.Model):
    _name = 'reso.property'
    _description = 'Reso Property'
    _order = 'name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Property Name', required=True, tracking=True)
    code = fields.Char(string='Code', size=10, required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, index=True)
    partner_id = fields.Many2one('res.partner', string='Legal Address')
    currency_id = fields.Many2one(
        related='company_id.currency_id', store=True, readonly=False,
        string='Currency')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')
    checkin_time = fields.Float(string='Check-in Time', default=14.0,
                                help="24h format")
    checkout_time = fields.Float(string='Check-out Time', default=12.0,
                                 help="24h format")
    image_1920 = fields.Image(string='Image')
    active = fields.Boolean(string='Active', default=True)
    room_ids = fields.One2many('reso.room', 'property_id',
                               string='Rooms')
    booking_ids = fields.One2many('reso.booking', 'property_id',
                                  string='Bookings')

    _code_uniq = models.Constraint(
        'unique(code)',
        'The property code must be unique.',
    )
