# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoWhatsAppMessage(models.Model):
    _name = 'reso.whatsapp.message'
    _description = 'Reso WhatsApp Log & Message'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Message ID', required=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Contact / Guest / Owner', required=True)
    phone = fields.Char(string='Phone Number', required=True)
    message_type = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound'),
    ], string='Direction', default='outbound', required=True)
    template_name = fields.Char(string='Template Name')
    body = fields.Text(string='Message Body', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ], string='Status', default='sent')
    booking_id = fields.Many2one('reso.booking', string='Related Booking')
    property_id = fields.Many2one('reso.property', string='Property')
    opt_in = fields.Boolean(string='Guest Opted-In', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('reso.whatsapp.message') or 'WA/00001'
        return super().create(vals_list)
