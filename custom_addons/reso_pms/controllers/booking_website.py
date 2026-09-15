# -*- coding: utf-8 -*-
import json
from datetime import datetime, date
from odoo import http, _
from odoo.http import request


class ResoWebsiteBookingController(http.Controller):

    def _json_response(self, data, status=200):
        headers = [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization'),
        ]
        return request.make_response(json.dumps(data, default=str), headers=headers, status=status)

    def _parse_dates(self, checkin_str, checkout_str):
        """Returns (checkin, checkout, error_message)."""
        try:
            checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
            checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None, None, 'Invalid dates — expected YYYY-MM-DD.'
        if checkout <= checkin:
            return None, None, 'Check-out date must be after check-in date.'
        return checkin, checkout, None

    @http.route([
        '/api/v1/website/properties',
        '/api/v1/website/availability',
        '/api/v1/website/booking/create',
        '/api/v1/payment/process',
    ], type='http', auth='public', methods=['OPTIONS'], csrf=False)
    def api_cors_options(self, **kwargs):
        return self._json_response({'status': 'ok'})

    @http.route('/api/v1/website/properties', type='http', auth='public', methods=['GET'], csrf=False)
    def list_properties(self, **kwargs):
        properties = request.env['reso.property'].sudo().search([('active', '=', True)])
        result = []
        for p in properties:
            room_types = request.env['reso.room.type'].sudo().search([('property_id', '=', p.id)])
            rt_list = []
            for rt in room_types:
                rate_plan = request.env['reso.rate.plan'].sudo().search([
                    ('property_id', '=', p.id),
                    ('room_type_id', '=', rt.id)
                ], limit=1)
                rt_list.append({
                    'id': rt.id,
                    'name': rt.name,
                    'max_guests': rt.max_guests,
                    'bed_type': rt.bed_type,
                    'base_price': rate_plan.base_price if rate_plan else 0.0,
                    'currency': rate_plan.currency_id.name if rate_plan and rate_plan.currency_id else request.env.company.currency_id.name,
                    'amenities': [a.name for a in rt.amenity_ids],
                })

            result.append({
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'city': p.city or '',
                'phone': p.phone or '',
                'email': p.email or '',
                'checkin_time': p.checkin_time,
                'checkout_time': p.checkout_time,
                'room_types': rt_list,
            })
        return self._json_response({'status': 'success', 'data': result})

    @http.route('/api/v1/website/availability', type='http', auth='public', methods=['POST'], csrf=False)
    def check_availability(self, **kwargs):
        data = request.httprequest.get_data()
        body = json.loads(data.decode('utf-8')) if data else {}

        property_id = body.get('property_id')
        checkin_str = body.get('checkin_date')
        checkout_str = body.get('checkout_date')
        guests = int(body.get('guests', 2))

        if not property_id or not checkin_str or not checkout_str:
            return self._json_response({'status': 'error', 'message': 'Missing property_id, checkin_date, or checkout_date'}, status=400)

        checkin, checkout, error = self._parse_dates(checkin_str, checkout_str)
        if error:
            return self._json_response({'status': 'error', 'message': error}, status=400)

        room_type_domain = [
            ('property_id', '=', int(property_id)),
            ('max_guests', '>=', guests),
        ]
        requested_type = body.get('room_type_id')
        if requested_type:
            room_type_domain.append(('id', '=', int(requested_type)))
        room_types = request.env['reso.room.type'].sudo().search(room_type_domain)

        available_types = []
        for rt in room_types:
            all_rooms = request.env['reso.room'].sudo().search([
                ('property_id', '=', int(property_id)),
                ('room_type_id', '=', rt.id),
                ('status', 'not in', ('maintenance', 'out_of_order')),
            ])

            # Check how many rooms are NOT booked during this window
            free_rooms = []
            for room in all_rooms:
                overlapping = request.env['reso.booking'].sudo().search([
                    ('room_id', '=', room.id),
                    ('state', 'in', ('hold', 'confirmed', 'checked_in')),
                    ('checkin_date', '<', checkout),
                    ('checkout_date', '>', checkin),
                ], limit=1)
                if not overlapping:
                    free_rooms.append(room)

            if free_rooms:
                rate_plan = request.env['reso.rate.plan'].sudo().search([
                    ('property_id', '=', int(property_id)),
                    ('room_type_id', '=', rt.id)
                ], limit=1)
                nights = (checkout - checkin).days
                total_price = nights * (rate_plan.base_price if rate_plan else 0.0)

                available_types.append({
                    'room_type_id': rt.id,
                    'name': rt.name,
                    'available_count': len(free_rooms),
                    'price_per_night': rate_plan.base_price if rate_plan else 0.0,
                    'total_price': total_price,
                    'currency': rate_plan.currency_id.name if rate_plan and rate_plan.currency_id else request.env.company.currency_id.name,
                })

        return self._json_response({'status': 'success', 'data': available_types})

    @http.route('/api/v1/website/booking/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_direct_booking(self, **kwargs):
        data = request.httprequest.get_data()
        body = json.loads(data.decode('utf-8')) if data else {}

        name = body.get('guest_name')
        email = body.get('guest_email')
        phone = body.get('guest_phone')
        property_id = body.get('property_id')
        room_type_id = body.get('room_type_id')
        checkin_str = body.get('checkin_date')
        checkout_str = body.get('checkout_date')
        payment_method = body.get('payment_method', 'bkash') # bkash, nagad, sslcommerz, stripe

        if not (name and phone and property_id and room_type_id and checkin_str and checkout_str):
            return self._json_response({'status': 'error', 'message': 'Missing required booking fields'}, status=400)

        checkin, checkout, error = self._parse_dates(checkin_str, checkout_str)
        if error:
            return self._json_response({'status': 'error', 'message': error}, status=400)

        # Partner lookup or creation
        partner = request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'phone': phone,
                'mobile': phone,
            })

        booking_vals = {
            'property_id': int(property_id),
            'partner_id': partner.id,
            'room_type_id': int(room_type_id),
            'checkin_date': checkin_str,
            'checkout_date': checkout_str,
            'adults': max(int(body.get('guests', 1) or 1), 1),
            'source': 'website',
            'state': 'hold',
            'note': f"Direct Website Booking via {payment_method.upper()}",
        }

        booking = request.env['reso.booking'].sudo().create(booking_vals)
        booking.action_assign_room()

        return self._json_response({
            'status': 'success',
            'data': {
                'booking_reference': booking.name,
                'guest_name': partner.name,
                'amount_total': booking.amount_total,
                'currency': booking.currency_id.name if booking.currency_id else request.env.company.currency_id.name,
                'state': booking.state,
                'payment_gateway_url': f"/api/v1/payment/process?ref={booking.name}&method={payment_method}",
            }
        })

    @http.route('/api/v1/payment/process', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def process_payment_callback(self, ref=None, method='bkash', **kwargs):
        """Simulates local & international gateway payment capture (bKash/Nagad/SSLCommerz/Stripe).

        Idempotent: an already-confirmed booking returns success with its
        current state instead of re-firing notifications.
        """
        booking = request.env['reso.booking'].sudo().search([('name', '=', ref)], limit=1)
        if not booking:
            return self._json_response({'status': 'error', 'message': 'Invalid booking reference'}, status=404)
        if booking.state == 'cancelled':
            return self._json_response({'status': 'error', 'message': f'Booking {booking.name} is cancelled.'}, status=409)
        if booking.state in ('confirmed', 'checked_in', 'checked_out', 'invoiced'):
            return self._json_response({
                'status': 'success',
                'message': f'Booking {booking.name} is already confirmed.',
                'booking_reference': booking.name,
                'payment_status': 'PAID',
                'state': booking.state,
            })

        booking.action_confirm()
        booking.send_whatsapp_notification('booking_confirmed')

        return self._json_response({
            'status': 'success',
            'message': f"Payment captured via {method.upper()} for booking {booking.name}.",
            'booking_reference': booking.name,
            'payment_status': 'PAID',
            'state': booking.state,
        })

    @http.route('/api/v1/whatsapp/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        """Two-Way WhatsApp Message Webhook & Automated FAQ Chatbot Receiver."""
        data = request.httprequest.get_data()
        body = json.loads(data.decode('utf-8')) if data else {}

        phone = body.get('phone')
        incoming_msg = body.get('message', '')

        if not phone or not incoming_msg:
            return self._json_response({'status': 'error', 'message': 'Missing phone or message'}, status=400)

        # Handle Opt-Out (GDPR / Privacy)
        if incoming_msg.strip().upper() == 'STOP':
            partner = request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
            if partner:
                partner.sudo().write({'comment': 'WhatsApp Opted-Out'})
            return self._json_response({'status': 'success', 'reply': 'You have been unsubscribed from WhatsApp notifications.'})

        # Match with Chatbot FAQ Rules
        rules = request.env['reso.whatsapp.chatbot.rule'].sudo().search([('active', '=', True)], order='sequence, id')
        matched_reply = None
        for rule in rules:
            if rule.match_message(incoming_msg):
                matched_reply = rule.response_template
                break

        if not matched_reply:
            matched_reply = "Thank you for contacting Reso Resort! Our Front Desk agent will reply to you shortly."

        # Log inbound message
        partner = request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = request.env['res.partner'].sudo().create({'name': f"WhatsApp Guest ({phone})", 'phone': phone})

        request.env['reso.whatsapp.message'].sudo().create({
            'partner_id': partner.id,
            'phone': phone,
            'message_type': 'inbound',
            'body': incoming_msg,
            'state': 'delivered',
        })

        # Send Bot Reply
        request.env['reso.whatsapp.message'].sudo().create({
            'partner_id': partner.id,
            'phone': phone,
            'message_type': 'outbound',
            'body': matched_reply,
            'state': 'sent',
        })

        return self._json_response({
            'status': 'success',
            'inbound_message': incoming_msg,
            'bot_reply': matched_reply,
        })
