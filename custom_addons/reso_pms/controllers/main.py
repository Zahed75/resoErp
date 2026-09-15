# -*- coding: utf-8 -*-
import json
from datetime import datetime, date, timedelta
from odoo import http
from odoo.http import request


class ResoPmsController(http.Controller):

    def _json_response(self, data, status=200):
        headers = [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization'),
        ]
        return request.make_response(json.dumps(data, default=str), headers=headers, status=status)

    @http.route('/api/v1/pms/options', type='http', auth='none', methods=['OPTIONS'], csrf=False)
    def api_options(self, **kwargs):
        return self._json_response({'status': 'ok'})

    @http.route('/api/v1/pms/dashboard/summary', type='http', auth='public', methods=['GET'], csrf=False)
    def get_dashboard_summary(self, property_id=None, **kwargs):
        """Executive Dashboard KPI Summary"""
        domain = [('active', '=', True)]
        if property_id:
            domain.append(('id', '=', int(property_id)))

        properties = request.env['reso.property'].sudo().search(domain)
        total_rooms = request.env['reso.room'].sudo().search_count([('active', '=', True)])
        occupied_rooms = request.env['reso.room'].sudo().search_count([('status', '=', 'occupied')])
        dirty_rooms = request.env['reso.room'].sudo().search_count([('housekeeping_status', '=', 'dirty')])
        maintenance_rooms = request.env['reso.room'].sudo().search_count([('status', '=', 'maintenance')])

        today = date.today()
        checkins_today = request.env['reso.booking'].sudo().search_count([
            ('checkin_date', '=', today),
            ('state', 'in', ('confirmed', 'checked_in'))
        ])
        checkouts_today = request.env['reso.booking'].sudo().search_count([
            ('checkout_date', '=', today),
            ('state', 'in', ('checked_in', 'checked_out'))
        ])

        bookings = request.env['reso.booking'].sudo().search([
            ('state', 'in', ('confirmed', 'checked_in', 'checked_out', 'invoiced'))
        ])
        total_revenue = sum(b.amount_total for b in bookings)
        occupancy_rate = round((occupied_rooms / max(total_rooms, 1)) * 100, 1)
        adr = round(total_revenue / max(len(bookings), 1), 2)
        revpar = round(total_revenue / max(total_rooms, 1), 2)

        # Fractional Ownership Stats
        shares = request.env['reso.owner.registry'].sudo().search([]) if 'reso.owner.registry' in request.env else []
        total_shares = len(shares)
        total_fractional_units = sum(s.shares_count for s in shares) if shares else 0

        data = {
            'property_count': len(properties),
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'dirty_rooms': dirty_rooms,
            'maintenance_rooms': maintenance_rooms,
            'occupancy_rate': occupancy_rate,
            'checkins_today': checkins_today,
            'checkouts_today': checkouts_today,
            'total_revenue': total_revenue,
            'adr': adr,
            'revpar': revpar,
            'currency': properties[0].currency_id.name if properties and properties[0].currency_id else request.env.company.currency_id.name,
            'fractional_owners': total_shares,
            'fractional_units': total_fractional_units,
        }
        return self._json_response({'status': 'success', 'data': data})

    @http.route('/api/v1/pms/bookings', type='http', auth='public', methods=['GET'], csrf=False)
    def get_bookings(self, state=None, **kwargs):
        domain = []
        if state:
            domain.append(('state', '=', state))
        bookings = request.env['reso.booking'].sudo().search(domain, order='checkin_date desc')
        result = []
        for b in bookings:
            result.append({
                'id': b.id,
                'name': b.name,
                'guest': b.partner_id.name,
                'phone': b.partner_id.phone or b.partner_id.mobile or '',
                'property': b.property_id.name,
                'room_type': b.room_type_id.name,
                'room': b.room_id.name if b.room_id else 'Unassigned',
                'checkin_date': str(b.checkin_date),
                'checkout_date': str(b.checkout_date),
                'adults': b.adults,
                'children': b.children,
                'source': b.source,
                'state': b.state,
                'amount_total': b.amount_total,
                'currency': b.currency_id.name if b.currency_id else request.env.company.currency_id.name,
            })
        return self._json_response({'status': 'success', 'data': result})

    @http.route('/api/v1/pms/rooms', type='http', auth='public', methods=['GET'], csrf=False)
    def get_rooms(self, **kwargs):
        rooms = request.env['reso.room'].sudo().search([])
        result = []
        for r in rooms:
            result.append({
                'id': r.id,
                'name': r.name,
                'property': r.property_id.name,
                'room_type': r.room_type_id.name,
                'floor': r.floor or 'N/A',
                'status': r.status,
                'housekeeping_status': r.housekeeping_status,
                'housekeeper': r.housekeeper_id.name if r.housekeeper_id else 'Unassigned',
                'last_cleaned': str(r.last_cleaned) if r.last_cleaned else None,
            })
        return self._json_response({'status': 'success', 'data': result})

    @http.route('/api/v1/pms/rooms/<int:room_id>/housekeeping', type='http', auth='public', methods=['POST', 'PUT'], csrf=False)
    def update_housekeeping(self, room_id, **kwargs):
        data = request.httprequest.get_data()
        body = json.loads(data.decode('utf-8')) if data else {}
        new_status = body.get('housekeeping_status')
        room = request.env['reso.room'].sudo().browse(room_id)
        if not room.exists():
            return self._json_response({'status': 'error', 'message': 'Room not found'}, status=404)

        if new_status == 'clean':
            room.action_mark_clean()
        elif new_status == 'dirty':
            room.action_mark_dirty()
        elif new_status == 'inspecting':
            room.action_mark_inspecting()
        elif new_status == 'in_progress':
            room.action_mark_in_progress()

        return self._json_response({
            'status': 'success',
            'data': {
                'id': room.id,
                'status': room.status,
                'housekeeping_status': room.housekeeping_status,
            }
        })

    @http.route('/api/v1/pms/reports/occupancy', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def get_occupancy_report(self, **kwargs):
        """Real monthly occupancy / ADR / RevPAR trend (trailing 12 months),
        folio revenue by outlet, and fractional owner distributions."""
        from calendar import monthrange

        Booking = request.env['reso.booking'].sudo()
        FolioLine = request.env['reso.booking.folio.line'].sudo()
        rooms_total = request.env['reso.room'].sudo().search_count(
            [('active', '=', True)]) or 1

        today = date.today()
        # Build the list of the last 12 month-start dates, oldest first.
        months = []
        cursor = today.replace(day=1)
        for _ in range(12):
            months.append(cursor)
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        months.reverse()

        labels, occupancy_rates, adr_values, revpar_values = [], [], [], []
        for month_start in months:
            next_month = (month_start + timedelta(days=32)).replace(day=1)
            days_in_month = monthrange(month_start.year, month_start.month)[1]

            bookings = Booking.search([
                ('checkout_date', '>', month_start),
                ('checkout_date', '<=', next_month),
                ('state', 'in', ('confirmed', 'checked_in', 'checked_out', 'invoiced')),
            ])
            revenue = sum(b.amount_total for b in bookings)
            room_nights = sum(
                max((b.checkout_date - b.checkin_date).days, 0) for b in bookings)
            available = rooms_total * days_in_month

            labels.append(month_start.strftime('%b %Y'))
            occupancy_rates.append(
                round(room_nights / available * 100, 1) if available else 0.0)
            adr_values.append(round(revenue / room_nights, 0) if room_nights else 0.0)
            revpar_values.append(round(revenue / available, 0) if available else 0.0)

        # Revenue by outlet: accommodation totals minus folio outlet charges,
        # then each folio outlet category on top.
        folio_by_outlet = {
            row['outlet_type']: row['amount']
            for row in FolioLine.read_group([], ['amount'], ['outlet_type'])
        }
        folio_room = folio_by_outlet.pop('room', 0.0) or 0.0
        all_bookings = Booking.search([('state', '!=', 'cancelled')])
        accommodation = sum(b.amount_total for b in all_bookings) \
            - sum(folio_by_outlet.values()) - folio_room
        outlet_names = dict(
            FolioLine._fields['outlet_type'].selection)
        gross_total = accommodation + sum(folio_by_outlet.values()) or 1.0
        revenue_by_outlet = [{
            'category': 'Room Accommodation & Villas',
            'gross': round(accommodation, 2),
            'percent': round(accommodation / gross_total * 100, 1),
        }]
        for outlet, amount in sorted(
                folio_by_outlet.items(), key=lambda kv: kv[1], reverse=True):
            revenue_by_outlet.append({
                'category': outlet_names.get(outlet, outlet),
                'gross': round(amount, 2),
                'percent': round(amount / gross_total * 100, 1),
            })

        # Fractional owner distribution statements (only when installed).
        ownership_yields = []
        if 'reso.distribution.line' in request.env:
            lines = request.env['reso.distribution.line'].sudo().search(
                [], order='amount desc', limit=50)
            for line in lines:
                ownership_yields.append({
                    'name': line.partner_id.name or '',
                    'property': line.registry_id.property_id.name or '',
                    'shares': line.fraction_percent,
                    'percent': '%.2f%%' % line.fraction_percent,
                    'dividend': round(line.amount, 2),
                    'status': 'Paid' if line.paid else 'Pending',
                })

        data = {
            'labels': labels,
            'occupancy_rates': occupancy_rates,
            'adr_values': adr_values,
            'revpar_values': revpar_values,
            'revenue_by_outlet': revenue_by_outlet,
            'ownership_yields': ownership_yields,
            'currency': request.env.company.currency_id.name,
        }
        return self._json_response({'status': 'success', 'data': data})

    @http.route('/api/v1/ownership/summary', type='http', auth='public', methods=['GET'], csrf=False)
    def get_ownership_summary(self, **kwargs):
        """Fractional Ownership Registry and Distribution overview"""
        owners = []
        if 'reso.owner.registry' in request.env:
            records = request.env['reso.owner.registry'].sudo().search([])
            for o in records:
                owners.append({
                    'id': o.id,
                    'owner_name': o.partner_id.name if o.partner_id else o.name,
                    'property': o.property_id.name if o.property_id else 'All Resorts',
                    'shares_count': o.shares_count if hasattr(o, 'shares_count') else 1,
                    'share_percentage': o.ownership_percentage if hasattr(o, 'ownership_percentage') else 5.0,
                    'status': 'active',
                })
        return self._json_response({'status': 'success', 'data': owners})
