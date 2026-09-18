# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RcloudReservation(models.Model):
    _name = 'rcloud.reservation'
    _description = 'Reservation'
    _order = 'arrival, id'
    _inherit = ['rcloud.property.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New',
        required=True, tracking=True)
    guest_id = fields.Many2one('res.partner', string='Guest', required=True)
    source = fields.Selection([
        ('direct', 'Direct'),
        ('ota', 'OTA'),
        ('corporate', 'Corporate'),
        ('walk_in', 'Walk-in'),
        ('agent', 'Travel Agent'),
    ], default='direct', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('hold', 'Hold'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], default='draft', required=True, tracking=True)
    arrival = fields.Date(required=True, default=fields.Date.today, index=True)
    departure = fields.Date(required=True)
    adults = fields.Integer(default=1, required=True)
    children = fields.Integer(default=0)
    room_type_id = fields.Many2one(
        'rcloud.room.type', required=True, ondelete='restrict')
    rate_plan_id = fields.Many2one('rcloud.rate.plan')
    room_id = fields.Many2one('rcloud.room', string='Assigned Room')
    folio_id = fields.Many2one('rcloud.folio', readonly=True, copy=False)
    line_ids = fields.One2many(
        'rcloud.reservation.line', 'reservation_id', string='Nightly Lines')
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True)
    amount_total = fields.Monetary(
        compute='_compute_amount_total', currency_field='currency_id',
        store=True)

    _reservation_dates = models.Constraint(
        'check(departure > arrival)',
        'Departure must be after arrival.')

    @api.constrains('property_id', 'room_type_id', 'rate_plan_id')
    def _check_property_consistency(self):
        for res in self:
            if res.room_type_id.property_id != res.property_id:
                raise ValidationError(
                    _('The room type must belong to the reservation property.'))
            if res.rate_plan_id and \
                    res.rate_plan_id.property_id != res.property_id:
                raise ValidationError(
                    _('The rate plan must belong to the reservation property.'))

    def action_print_folio(self):
        self.ensure_one()
        if not self.folio_id:
            raise UserError(_('The reservation has no folio yet.'))
        report = self.env.ref(
            'rcloud_pms_account.action_report_folio',
            raise_if_not_found=False)
        if not report:
            raise UserError(_('The folio report is not available.'))
        return report.report_action(self.folio_id)

    @api.depends('line_ids.rate')
    def _compute_amount_total(self):
        for res in self:
            res.amount_total = sum(line.rate for line in res.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rcloud.reservation') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------- helpers
    def _nights(self):
        self.ensure_one()
        return (self.departure - self.arrival).days

    def _buckets(self):
        self.ensure_one()
        Availability = self.env['rcloud.availability'].sudo()
        buckets = Availability.search_buckets(
            self.property_id.id, self.room_type_id.id,
            self.arrival, self.departure)
        if len(buckets) != self._nights():
            raise UserError(
                _('Inventory is not open for %s between %s and %s. '
                  'Generate availability first.') % (
                    self.room_type_id.name, self.arrival, self.departure))
        return buckets

    def _generate_lines(self):
        """One line per room-night, priced from the rate calendar."""
        self.ensure_one()
        Calendar = self.env['rcloud.rate.calendar'].sudo()
        lines = []
        for i in range(self._nights()):
            day = self.arrival + timedelta(days=i)
            rate, _min_stay, _cta = Calendar.rate_for(
                self.rate_plan_id, day) if self.rate_plan_id else \
                (self.room_type_id.default_rate, 1, False)
            lines.append((0, 0, {
                'room_type_id': self.room_type_id.id,
                'rate_plan_id': self.rate_plan_id.id,
                'date': day,
                'rate': rate,
            }))
        self.line_ids = lines

    def _release_inventory(self):
        for bucket in self._buckets():
            bucket.release(1)

    # ---------------------------------------------------------- lifecycle
    def action_hold(self):
        """Draft -> Hold: block inventory, lines generated."""
        for res in self:
            if res.state != 'draft':
                raise UserError(_('Only draft reservations can be held.'))
            for bucket in res._buckets():
                bucket.allocate(1)
            res._generate_lines()
            res.state = 'hold'
            res.message_post(body=_('Reservation placed on hold.'))

    def action_confirm(self):
        for res in self:
            if res.state not in ('draft', 'hold'):
                raise UserError(
                    _('Only draft or hold reservations can be confirmed.'))
            res._check_min_stay()
            if res.state == 'draft':
                for bucket in res._buckets():
                    bucket.allocate(1)
            if not res.line_ids:
                res._generate_lines()
            res.state = 'confirmed'
            res.message_post(body=_('Reservation confirmed.'))

    def _check_min_stay(self):
        self.ensure_one()
        Calendar = self.env['rcloud.rate.calendar'].sudo()
        if self.rate_plan_id:
            _rate, min_stay, _cta = Calendar.rate_for(
                self.rate_plan_id, self.arrival)
            if self._nights() < min_stay:
                raise UserError(
                    _('This rate requires a minimum stay of %s nights.') %
                    min_stay)

    def action_check_in(self):
        for res in self:
            if res.state != 'confirmed':
                raise UserError(_('Only confirmed guests can check in.'))
            if not res.room_id:
                res.action_assign_room()
            if not res.room_id:
                raise UserError(_('No room available of this type to assign.'))
            res.room_id.write({'status': 'occupied',
                               'housekeeping_state': 'dirty'})
            if not res.folio_id:
                res.folio_id = self.env['rcloud.folio'].create({
                    'reservation_id': res.id,
                    'partner_id': res.guest_id.id,
                }).id
            res.state = 'checked_in'
            res.message_post(body=_(
                'Checked in to room %s.') % res.room_id.name)

    def action_assign_room(self):
        for res in self:
            room = self.env['rcloud.room'].search([
                ('property_id', '=', res.property_id.id),
                ('room_type_id', '=', res.room_type_id.id),
                ('status', '!=', 'occupied'),
                ('is_ooo', '=', False),
            ], limit=1)
            res.room_id = room

    def action_check_out(self):
        for res in self:
            if res.state != 'checked_in':
                raise UserError(_('Only in-house guests can check out.'))
            if res.room_id:
                res.room_id.write({'status': 'vacant_dirty',
                                   'housekeeping_state': 'dirty'})
            if res.folio_id:
                res.folio_id.action_close()
            res.state = 'checked_out'
            res.message_post(body=_('Checked out.'))

    def action_cancel(self):
        """Explicit, permissioned reversal: releases inventory."""
        for res in self:
            if res.state not in ('hold', 'confirmed'):
                raise UserError(
                    _('Only hold or confirmed reservations can be cancelled.'))
            res._release_inventory()
            res.state = 'cancelled'
            res.message_post(body=_('Reservation cancelled, inventory released.'))

    def action_no_show(self):
        """Manager-only transition."""
        if not self.env.user.has_group('rcloud_base.group_hotel_manager'):
            raise UserError(
                _('Only hotel managers can mark a no-show.'))
        for res in self:
            if res.state != 'confirmed':
                raise UserError(_('Only confirmed reservations can be no-show.'))
            res._release_inventory()
            res.state = 'no_show'
            res.message_post(body=_('Marked as no-show.'))


class RcloudReservationLine(models.Model):
    _name = 'rcloud.reservation.line'
    _description = 'Reservation Nightly Line'
    _order = 'date'

    reservation_id = fields.Many2one(
        'rcloud.reservation', required=True, ondelete='cascade', index=True)
    room_id = fields.Many2one('rcloud.room')
    room_type_id = fields.Many2one('rcloud.room.type', required=True)
    rate_plan_id = fields.Many2one('rcloud.rate.plan')
    date = fields.Date(required=True)
    rate = fields.Monetary(required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        related='reservation_id.currency_id', store=True)

    _line_day_uniq = models.Constraint(
        'unique(reservation_id, date)',
        'A reservation can only have one line per night.')
