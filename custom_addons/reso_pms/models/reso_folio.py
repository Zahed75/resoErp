# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoBookingFolioLine(models.Model):
    _name = 'reso.booking.folio.line'
    _description = 'Reso Booking Folio Line'

    booking_id = fields.Many2one('reso.booking', string='Booking', required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    outlet_type = fields.Selection([
        ('room', 'Room Charge'),
        ('restaurant', 'Restaurant POS'),
        ('bar', 'Bar & Lounge'),
        ('spa', 'Spa & Wellness'),
        ('excursion', 'Tour / Excursion'),
        ('laundry', 'Laundry & Service'),
        ('minibar', 'Minibar'),
    ], string='Outlet Category', default='room', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    product_id = fields.Many2one('product.product', string='Service / Item')
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Monetary(string='Unit Price', required=True, currency_field='currency_id')
    amount = fields.Monetary(string='Total Amount', compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='booking_id.currency_id', store=True, string='Currency')
    reference = fields.Char(string='POS Receipt / Ticket Ref')

    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.price_unit
