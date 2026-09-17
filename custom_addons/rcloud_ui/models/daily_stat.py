# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class RcloudPmsDailyStat(models.Model):
    """Materialized daily statistics per property, populated by a nightly
    cron. Trend charts read this table instead of aggregating bookings."""

    _name = 'rcloud.pms.daily.stat'
    _description = 'PMS Daily Statistic'
    _order = 'date desc'

    property_id = fields.Many2one('rcloud.property', required=True,
                                  ondelete='cascade', index=True)
    date = fields.Date(required=True, index=True)
    occupancy_rate = fields.Float()
    adr = fields.Monetary(currency_field='currency_id')
    revpar = fields.Monetary(currency_field='currency_id')
    revenue = fields.Monetary(currency_field='currency_id')
    arrivals = fields.Integer()
    departures = fields.Integer()
    currency_id = fields.Many2one(
        related='property_id.currency_id', store=True)

    _stat_day_uniq = models.Constraint(
        'unique(property_id, date)',
        'A daily stat already exists for this property and date.')

    @api.model
    def _compute_for_date(self, prop, day):
        Reservation = self.env['rcloud.reservation'].sudo()
        Availability = self.env['rcloud.availability'].sudo()
        domain_base = [('property_id', '=', prop.id)]
        arrivals = Reservation.search_count(domain_base + [
            ('arrival', '=', day),
            ('state', 'in', ('hold', 'confirmed', 'checked_in')),
        ])
        departures = Reservation.search_count(domain_base + [
            ('departure', '=', day), ('state', '=', 'checked_in')])
        departed = Reservation.search(domain_base + [
            ('departure', '=', day),
            ('state', 'in', ('checked_out', 'invoiced')),
        ])
        revenue = sum(r.amount_total for r in departed)
        room_nights = sum(
            max((r.departure - r.arrival).days, 0) for r in departed)
        buckets = Availability.search([
            ('property_id', '=', prop.id),
            ('date', '=', day),
        ])
        total_rooms = sum(buckets.mapped('total')) or prop.total_rooms or 1
        occupied = Reservation.search_count(domain_base + [
            ('state', '=', 'checked_in'),
            ('arrival', '<=', day), ('departure', '>', day),
        ])
        occupancy = round(occupied / total_rooms * 100, 1) if total_rooms else 0.0
        adr = round(revenue / room_nights, 2) if room_nights else 0.0
        revpar = round(revenue / total_rooms, 2) if total_rooms else 0.0

        stat = self.search([('property_id', '=', prop.id), ('date', '=', day)],
                           limit=1)
        values = {
            'occupancy_rate': occupancy,
            'adr': adr,
            'revpar': revpar,
            'revenue': revenue,
            'arrivals': arrivals,
            'departures': departures,
        }
        if stat:
            stat.write(values)
        else:
            self.create(dict(values, property_id=prop.id, date=day))

    @api.model
    def cron_nightly(self):
        yesterday = fields.Date.today() - timedelta(days=1)
        props = self.env['rcloud.property'].sudo().search([])
        for prop in props:
            self._compute_for_date(prop, yesterday)
        return True
