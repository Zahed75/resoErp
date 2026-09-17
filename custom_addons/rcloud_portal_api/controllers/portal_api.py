# -*- coding: utf-8 -*-
import json
from datetime import datetime

from odoo import http
from odoo.http import request


def _json(data, status=200):
    return request.make_response(
        json.dumps(data, default=str),
        [('Content-Type', 'application/json'),
         ('Access-Control-Allow-Origin', '*'),
         ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
         ('Access-Control-Allow-Headers', 'Content-Type')],
        status=status)


class RcloudPortalApi(http.Controller):

    def _parse_dates(self, checkin_str, checkout_str):
        try:
            checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
            checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None, None, 'Invalid dates — expected YYYY-MM-DD.'
        if checkout <= checkin:
            return None, None, 'Check-out must be after check-in.'
        return checkin, checkout, None

    @http.route('/rcloud/api/v1/properties', type='http', auth='public',
                methods=['GET'], csrf=False)
    def list_properties(self, **kw):
        props = request.env['rcloud.property'].sudo().search(
            [('active', '=', True)])
        data = []
        for p in props:
            room_types = request.env['rcloud.room.type'].sudo().search([
                ('property_id', '=', p.id)])
            data.append({
                'id': p.id, 'name': p.name, 'city': p.city or '',
                'phone': p.phone or '', 'email': p.email or '',
                'currency': p.currency_id.name,
                'room_types': [{
                    'id': rt.id, 'name': rt.name,
                    'base_occupancy': rt.base_occupancy,
                    'max_occupancy': rt.max_occupancy,
                    'default_rate': rt.default_rate,
                } for rt in room_types],
            })
        return _json({'status': 'success', 'data': data})

    @http.route('/rcloud/api/v1/availability', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    def check_availability(self, **kw):
        body = json.loads(request.httprequest.data or b'{}')
        checkin, checkout, error = self._parse_dates(
            body.get('checkin'), body.get('checkout'))
        if error:
            return _json({'status': 'error', 'message': error}, 400)
        property_id = int(body.get('property_id', 0))
        guests = int(body.get('guests', 2))
        Availability = request.env['rcloud.availability'].sudo()
        result = []
        room_types = request.env['rcloud.room.type'].sudo().search([
            ('property_id', '=', property_id),
            ('max_occupancy', '>=', guests),
        ])
        for rt in room_types:
            buckets = Availability.search([
                ('property_id', '=', property_id),
                ('room_type_id', '=', rt.id),
                ('date', '>=', checkin), ('date', '<', checkout),
            ], order='date')
            if len(buckets) != (checkout - checkin).days:
                continue  # inventory not open for the full window
            free = min(b.total - b.sold - b.blocked for b in buckets)
            if free <= 0:
                continue
            nights = (checkout - checkin).days
            result.append({
                'room_type_id': rt.id, 'name': rt.name,
                'available': free, 'price_per_night': rt.default_rate,
                'total': rt.default_rate * nights,
                'currency': rt.currency_id.name,
            })
        return _json({'status': 'success', 'data': result})

    @http.route('/rcloud/api/v1/bookings', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    def create_booking(self, **kw):
        body = json.loads(request.httprequest.data or b'{}')
        required = ('guest_name', 'guest_phone', 'property_id',
                    'room_type_id', 'checkin', 'checkout')
        missing = [f for f in required if not body.get(f)]
        if missing:
            return _json({'status': 'error',
                          'message': 'Missing: %s' % ', '.join(missing)}, 400)
        checkin, checkout, error = self._parse_dates(
            body['checkin'], body['checkout'])
        if error:
            return _json({'status': 'error', 'message': error}, 400)

        env = request.env
        partner = env['res.partner'].sudo().search(
            [('phone', '=', body['guest_phone'])], limit=1)
        if not partner:
            partner = env['res.partner'].sudo().create({
                'name': body['guest_name'],
                'phone': body['guest_phone'],
                'email': body.get('guest_email', ''),
            })
        res = env['rcloud.reservation'].sudo().create({
            'property_id': int(body['property_id']),
            'room_type_id': int(body['room_type_id']),
            'guest_id': partner.id,
            'arrival': checkin,
            'departure': checkout,
            'adults': max(int(body.get('guests', 1)), 1),
            'source': 'direct' if body.get('source') != 'walk_in' else 'walk_in',
            'state': 'draft',
        })
        try:
            res.action_confirm()
        except Exception as exc:
            return _json({'status': 'error',
                          'message': str(exc)}, 409)
        return _json({'status': 'success', 'data': {
            'reference': res.name,
            'state': res.state,
            'amount_total': res.amount_total,
            'currency': res.currency_id.name,
        }})
