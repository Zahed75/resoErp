# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoCrmLead(models.Model):
    _inherit = 'crm.lead'

    lead_type = fields.Selection([
        ('guest', 'Guest Booking Lead'),
        ('investor', 'Fractional Investor Lead'),
        ('corporate', 'Corporate / Event Lead'),
        ('agent', 'Travel Agent Lead'),
    ], string='Resort Lead Type', default='guest', tracking=True)

    property_id = fields.Many2one(
        'reso.property', string='Target Property', tracking=True)
    room_type_id = fields.Many2one(
        'reso.room.type', string='Preferred Room Type',
        domain="[('property_id', '=', property_id)]")
    preferred_checkin = fields.Date(string='Preferred Check-in')
    preferred_checkout = fields.Date(string='Preferred Check-out')
    guests_count = fields.Integer(string='Guests Count', default=2)

    # Investor specific
    investor_budget = fields.Monetary(string='Investor Budget', currency_field='company_currency')
    investor_units_interested = fields.Integer(string='Units/Fractions Interested', default=1)

    lead_score = fields.Integer(string='Lead Score', compute='_compute_lead_score', store=True)
    whatsapp_opt_in = fields.Boolean(string='WhatsApp Opt-In', default=True)

    @api.depends('expected_revenue', 'investor_budget', 'lead_type', 'stage_id')
    def _compute_lead_score(self):
        for lead in self:
            score = 10
            if lead.lead_type == 'investor':
                if lead.investor_budget > 5000000:
                    score += 50
                elif lead.investor_budget > 1000000:
                    score += 30
            elif lead.lead_type == 'guest':
                if lead.expected_revenue > 100000:
                    score += 30
                elif lead.expected_revenue > 30000:
                    score += 15

            if lead.partner_id and (lead.partner_id.phone or lead.partner_id.mobile):
                score += 10
            if lead.whatsapp_opt_in:
                score += 10

            lead.lead_score = score

    def action_convert_to_booking(self):
        """Converts CRM Lead directly into a Reso Booking."""
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_('Please assign a contact (Guest) before creating a booking.'))
        if not self.property_id or not self.room_type_id:
            raise ValidationError(_('Please set the Property and Room Type on the lead.'))

        booking_vals = {
            'property_id': self.property_id.id,
            'partner_id': self.partner_id.id,
            'room_type_id': self.room_type_id.id,
            'checkin_date': self.preferred_checkin or fields.Date.today(),
            'checkout_date': self.preferred_checkout or fields.Date.add(fields.Date.today(), days=2),
            'adults': self.guests_count or 2,
            'source': 'direct',
            'state': 'hold',
            'note': f"Created from CRM Lead: {self.name}",
        }
        booking = self.env['reso.booking'].create(booking_vals)
        self.write({
            'description': (self.description or '') + f"\nConverted to Booking {booking.name}"
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'reso.booking',
            'res_id': booking.id,
            'view_mode': 'form',
            'target': 'current',
        }
