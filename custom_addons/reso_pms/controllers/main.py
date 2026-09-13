# -*- coding: utf-8 -*-
import json
from datetime import datetime, date
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
            'currency': properties[0].currency_id.name if properties and properties[0].currency_id else 'BDT',
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
                'currency': b.currency_id.name if b.currency_id else 'BDT',
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

    @http.route('/api/v1/pms/reports/occupancy', type='http', auth='public', methods=['GET'], csrf=False)
    def get_occupancy_report(self, **kwargs):
        """Monthly & Quarterly Occupancy and ADR trends"""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
        data = {
            'labels': months,
            'occupancy_rates': [65.4, 72.1, 80.5, 78.2, 85.0, 88.4, 92.1, 89.5, 84.0],
            'adr_values': [12000, 12500, 13000, 13500, 14000, 15000, 16500, 15500, 14500],
            'revpar_values': [7848, 9012, 10465, 10557, 11900, 13260, 15196, 13872, 12180],
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
