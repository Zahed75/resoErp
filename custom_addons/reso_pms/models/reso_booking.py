# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoBooking(models.Model):
    _name = 'reso.booking'
    _description = 'Reso Booking'
    _order = 'checkin_date, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Booking Reference', required=True,
                       readonly=True, copy=False, default='New')
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')
    partner_id = fields.Many2one('res.partner', string='Guest',
                                 required=True)
    room_type_id = fields.Many2one('reso.room.type', string='Room Type',
                                   required=True)
    rate_plan_id = fields.Many2one('reso.rate.plan', string='Rate Plan',
                                  domain="[('property_id', '=', property_id), ('room_type_id', '=', room_type_id)]")
    room_id = fields.Many2one(
        'reso.room', string='Room',
        domain="[('property_id', '=', property_id), "
               "('room_type_id', '=', room_type_id)]")
    checkin_date = fields.Date(string='Check-in Date', required=True,
                               default=fields.Date.today)
    checkout_date = fields.Date(
        string='Check-out Date', required=True,
        default=lambda self: fields.Date.add(fields.Date.today(), days=1))
    adults = fields.Integer(string='Adults', default=1)
    children = fields.Integer(string='Children', default=0)
    source = fields.Selection([
        ('direct', 'Direct'),
        ('website', 'Website'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('ota', 'OTA'),
        ('agent', 'Travel Agent'),
        ('walk_in', 'Walk-in'),
    ], string='Source', default='direct')
    state = fields.Selection([
        ('hold', 'Hold'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='hold', readonly=True, copy=False,
        tracking=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_total',
                                   store=True,
                                   currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id',
                                  store=True, string='Currency')
    invoice_id = fields.Many2one('account.move', string='Folio Invoice', readonly=True, copy=False)
    whatsapp_message_ids = fields.One2many('reso.whatsapp.message', 'booking_id', string='WhatsApp Logs')
    folio_line_ids = fields.One2many('reso.booking.folio.line', 'booking_id', string='Folio Charges (F&B / Outlets)')
    note = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'reso.booking') or 'New'
        bookings = super().create(vals_list)
        for booking in bookings:
            booking._check_room_availability()
        return bookings

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('checkin_date', 'checkout_date', 'room_id', 'room_type_id', 'property_id')):
            for booking in self:
                if booking.state not in ('cancelled', 'checked_out', 'invoiced'):
                    booking._check_room_availability()
        return res

    @api.depends('checkin_date', 'checkout_date', 'room_type_id',
                 'property_id', 'rate_plan_id', 'folio_line_ids.amount')
    def _compute_amount_total(self):
        """Dynamic Rate & Seasonal Pricing Engine + Outlet Folio Charges"""
        for booking in self:
            booking.amount_total = 0.0
            if not (booking.checkin_date and booking.checkout_date):
                continue
            nights = (booking.checkout_date - booking.checkin_date).days
            if nights <= 0:
                continue

            rate_plan = booking.rate_plan_id
            if not rate_plan:
                rate_plan = self.env['reso.rate.plan'].search([
                    ('property_id', '=', booking.property_id.id),
                    ('room_type_id', '=', booking.room_type_id.id),
                ], order='base_price asc', limit=1)

            total = 0.0
            if rate_plan:
                curr_date = booking.checkin_date
                while curr_date < booking.checkout_date:
                    # Check for seasonal override for this date
                    season = rate_plan.season_line_ids.filtered(
                        lambda s: s.date_from <= curr_date <= s.date_to
                    )
                    if season:
                        total += season[0].price
                    else:
                        total += rate_plan.base_price
                    curr_date += timedelta(days=1)

            # Add outlet folio charges
            extra_folio = sum(line.amount for line in booking.folio_line_ids)
            booking.amount_total = total + extra_folio

    @api.constrains('checkin_date', 'checkout_date')
    def _check_dates(self):
        for booking in self:
            if booking.checkin_date and booking.checkout_date and \
                    booking.checkout_date <= booking.checkin_date:
                raise ValidationError(
                    _('The check-out date must be after the check-in date.'))

    @api.constrains('adults')
    def _check_adults(self):
        for booking in self:
            if booking.adults < 1:
                raise ValidationError(
                    _('A booking must have at least one adult.'))

    def _check_room_availability(self):
        """Availability Engine: Ensures no overlapping bookings for the assigned room."""
        for booking in self:
            if not booking.room_id or booking.state == 'cancelled':
                continue
            overlapping = self.search([
                ('id', '!=', booking.id),
                ('room_id', '=', booking.room_id.id),
                ('state', 'in', ('hold', 'confirmed', 'checked_in')),
                ('checkin_date', '<', booking.checkout_date),
                ('checkout_date', '>', booking.checkin_date),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    _('Room %s is already booked for overlapping dates by booking %s (%s to %s).') % (
                        booking.room_id.name, overlapping.name, overlapping.checkin_date, overlapping.checkout_date
                    ))

    def action_assign_room(self):
        """Auto assigns an available room of the selected room type."""
        for booking in self:
            if booking.room_id:
                continue
            all_rooms = self.env['reso.room'].search([
                ('property_id', '=', booking.property_id.id),
                ('room_type_id', '=', booking.room_type_id.id),
                ('status', '!=', 'out_of_order'),
            ])
            for room in all_rooms:
                overlapping = self.search([
                    ('id', '!=', booking.id),
                    ('room_id', '=', room.id),
                    ('state', 'in', ('hold', 'confirmed', 'checked_in')),
                    ('checkin_date', '<', booking.checkout_date),
                    ('checkout_date', '>', booking.checkin_date),
                ], limit=1)
                if not overlapping:
                    booking.room_id = room.id
                    break

    def action_confirm(self):
        for rec in self:
            if rec.state == 'hold':
                if not rec.room_id:
                    rec.action_assign_room()
                rec._check_room_availability()
                rec.state = 'confirmed'
                rec.send_whatsapp_notification('booking_confirmed')

    def action_check_in(self):
        for rec in self:
            if rec.state == 'confirmed':
                if not rec.room_id:
                    rec.action_assign_room()
                    if not rec.room_id:
                        raise ValidationError(_('Please assign a room before checking in.'))
                rec._check_room_availability()
                rec.state = 'checked_in'
                rec.room_id.status = 'occupied'
                rec.send_whatsapp_notification('check_in')

    def action_check_out(self):
        for rec in self:
            if rec.state == 'checked_in':
                rec.state = 'checked_out'
                if rec.room_id:
                    rec.room_id.status = 'cleaning'
                    rec.room_id.housekeeping_status = 'dirty'
                rec.send_whatsapp_notification('check_out')

    def action_create_invoice(self):
        """Generates Odoo Folio Invoice for the booking total."""
        for rec in self:
            if rec.invoice_id:
                continue
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'currency_id': rec.currency_id.id,
                'invoice_origin': rec.name,
                'invoice_line_ids': [(0, 0, {
                    'name': f'Resort Accommodation ({rec.room_type_id.name}) - {rec.checkin_date} to {rec.checkout_date}',
                    'quantity': max((rec.checkout_date - rec.checkin_date).days, 1),
                    'price_unit': rec.amount_total / max((rec.checkout_date - rec.checkin_date).days, 1),
                })],
            }
            invoice = self.env['account.move'].create(invoice_vals)
            rec.invoice_id = invoice.id
            rec.state = 'invoiced'

    def action_cancel(self):
        for rec in self:
            if rec.state in ('hold', 'confirmed'):
                rec.state = 'cancelled'

    def send_whatsapp_notification(self, template_key):
        """Logs automated WhatsApp communication against guest record."""
        for rec in self:
            phone = rec.partner_id.phone or rec.partner_id.mobile
            if not phone:
                continue
            msg = ""
            if template_key == 'booking_confirmed':
                msg = f"Dear {rec.partner_id.name}, your booking {rec.name} at {rec.property_id.name} is confirmed for {rec.checkin_date}. Total: {rec.amount_total} {rec.currency_id.name or ''}."
            elif template_key == 'check_in':
                msg = f"Welcome to {rec.property_id.name}, {rec.partner_id.name}! You are checked into Room {rec.room_id.name or ''}. Enjoy your stay!"
            elif template_key == 'check_out':
                msg = f"Thank you for staying at {rec.property_id.name}, {rec.partner_id.name}. We hope to see you again soon!"

            if msg:
                self.env['reso.whatsapp.message'].create({
                    'partner_id': rec.partner_id.id,
                    'phone': phone,
                    'message_type': 'outbound',
                    'template_name': template_key,
                    'body': msg,
                    'booking_id': rec.id,
                    'property_id': rec.property_id.id,
                    'state': 'sent',
                })
