# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class RcloudReservation(models.Model):
    _inherit = 'rcloud.reservation'

    @api.model
    def get_dashboard_stats(self, property_id=None):
        """Single-call KPI payload for the PMS dashboard (spec 2.5).

        Respects the property switcher; all aggregations use search_count /
        read_group style queries, never record loops over large datasets
        for the headline KPIs.
        """
        today = fields.Date.today()
        domain = []
        if property_id:
            domain.append(('property_id', '=', property_id))
        prop_domain = [('active', '=', True)]
        if property_id:
            prop_domain.append(('id', '=', property_id))
        room_domain = list(domain)

        Property = self.env['rcloud.property'].sudo()
        Reservation = self.env['rcloud.reservation'].sudo()
        Room = self.env['rcloud.room'].sudo()
        Availability = self.env['rcloud.availability'].sudo()
        DailyStat = self.env['rcloud.pms.daily.stat'].sudo()

        rooms_total = Room.search_count(room_domain)
        occupied = Room.search_count(
            room_domain + [('status', '=', 'occupied')])
        dirty = Room.search_count(
            room_domain + [('housekeeping_state', '=', 'dirty')])
        ooo = Room.search_count(room_domain + [('is_ooo', '=', True)])
        clean = rooms_total - occupied - dirty - ooo

        arrivals_today = Reservation.search_count(domain + [
            ('arrival', '=', today),
            ('state', 'in', ('hold', 'confirmed'))])
        departures_today = Reservation.search_count(domain + [
            ('departure', '=', today), ('state', '=', 'checked_in')])
        in_house = Reservation.search_count(
            domain + [('state', '=', 'checked_in')])

        date_from = today - timedelta(days=30)
        recent = Reservation.search(domain + [
            ('departure', '>=', date_from),
            ('state', 'in', ('checked_out', 'invoiced')),
        ])
        revenue = sum(r.amount_total for r in recent)
        room_nights = sum(max((r.departure - r.arrival).days, 0) for r in recent)
        buckets = Availability.search([
            ('date', '>=', date_from), ('date', '<=', today),
        ] + ([('property_id', '=', property_id)] if property_id else []))
        available = sum(buckets.mapped('total')) or (rooms_total * 30) or 1
        occupancy = round(occupied / rooms_total * 100, 1) if rooms_total else 0.0
        adr = round(revenue / room_nights, 2) if room_nights else 0.0
        revpar = round(revenue / available, 2) if available else 0.0

        # Prior-period deltas (previous 30 days)
        prev_from = today - timedelta(days=60)
        prev = Reservation.search(domain + [
            ('departure', '>=', prev_from), ('departure', '<', date_from),
            ('state', 'in', ('checked_out', 'invoiced')),
        ])
        prev_revenue = sum(r.amount_total for r in prev)

        # 30-day trend from materialized stats
        stats = DailyStat.search([
            ('date', '>=', date_from), ('date', '<=', today),
        ] + ([('property_id', '=', property_id)] if property_id else []))
        trend = [{
            'date': str(s.date), 'occupancy': s.occupancy_rate,
            'revenue': s.revenue,
        } for s in sorted(stats, key=lambda s: s.date)]

        # Revenue by reservation source (last 30 days)
        by_source = []
        grouped = Reservation.read_group(
            domain + [
                ('departure', '>=', date_from),
                ('state', 'in', ('confirmed', 'checked_in', 'checked_out', 'invoiced')),
            ],
            ['amount_total'], ['source'])
        by_source = [{
            'source': g['source'] or 'other',
            'amount': g['amount_total'] or 0.0,
        } for g in grouped]

        # Today's movements lists (bounded)
        arrivals = Reservation.search_read(domain + [
            ('arrival', '=', today), ('state', 'in', ('hold', 'confirmed'))],
            ['id', 'name', 'guest_id', 'room_type_id', 'state'],
            limit=30, order='name')
        departures = Reservation.search_read(domain + [
            ('departure', '=', today), ('state', '=', 'checked_in')],
            ['id', 'name', 'guest_id', 'room_id', 'state'],
            limit=30, order='name')
        inhouse = Reservation.search_read(domain + [
            ('state', '=', 'checked_in')],
            ['id', 'name', 'guest_id', 'room_id', 'departure'],
            limit=30, order='room_id')

        rooms = Room.search_read(
            room_domain,
            ['id', 'name', 'status', 'housekeeping_state', 'is_ooo'],
            limit=400, order='name')

        return {
            'today': str(today),
            'kpis': {
                'occupancy': occupancy,
                'adr': adr,
                'revpar': revpar,
                'arrivals_today': arrivals_today,
                'departures_today': departures_today,
                'in_house': in_house,
                'revenue_30d': round(revenue, 2),
                'revenue_prev_30d': round(prev_revenue, 2),
                'rooms_total': rooms_total,
                'occupied': occupied,
                'dirty': dirty,
                'ooo': ooo,
                'clean': clean,
            },
            'trend': trend,
            'revenue_by_source': by_source,
            'arrivals': arrivals,
            'departures': departures,
            'inhouse': inhouse,
            'rooms': rooms,
        }
