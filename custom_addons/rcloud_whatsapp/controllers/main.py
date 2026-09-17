# -*- coding: utf-8 -*-
import json

from odoo import http, _
from odoo.http import request


class RcloudWhatsappController(http.Controller):

    def _json(self, data, status=200):
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
            status=status)

    @http.route('/rcloud/whatsapp/webhook', type='http', auth='public',
                methods=['POST'], csrf=False)
    def webhook(self, **kwargs):
        """Inbound message receiver: logs both directions, honours STOP
        opt-outs and answers through the chatbot rules."""
        raw = request.httprequest.get_data()
        body = json.loads(raw.decode('utf-8')) if raw else kwargs or {}
        phone = body.get('phone')
        message = (body.get('message') or '').strip()
        if not phone or not message:
            return self._json(
                {'status': 'error', 'message': 'Missing phone or message'},
                status=400)

        Partner = request.env['res.partner'].sudo()
        partner = Partner.search(
            ['|', ('phone', '=', phone), ('whatsapp_number', '=', phone)],
            limit=1)
        if not partner:
            partner = Partner.create({
                'name': 'WhatsApp Guest (%s)' % phone,
                'whatsapp_number': phone,
            })

        Message = request.env['rcloud.whatsapp.message'].sudo()
        Message.create({
            'partner_id': partner.id, 'phone': phone,
            'direction': 'in', 'body': message, 'state': 'delivered',
        })

        if message.upper() == 'STOP':
            partner.write({
                'whatsapp_opt_out': True, 'whatsapp_opt_in': False})
            reply = _('You have been unsubscribed from WhatsApp '
                      'notifications. Text START to opt back in.')
            Message.create({
                'partner_id': partner.id, 'phone': phone,
                'direction': 'out', 'body': reply, 'state': 'sent',
            })
            return self._json({'status': 'ok', 'bot_reply': reply})

        Rule = request.env['rcloud.whatsapp.chatbot.rule'].sudo()
        reply = None
        for rule in Rule.search([('active', '=', True)]):
            if rule.match_message(message):
                reply = rule.response_template
                break
        if not reply:
            reply = _('Thank you for contacting us. Our team will reply '
                      'shortly.')

        Message.create({
            'partner_id': partner.id, 'phone': phone,
            'direction': 'out', 'body': reply, 'state': 'sent',
        })
        return self._json({'status': 'ok', 'bot_reply': reply})

    @http.route('/rcloud/whatsapp/status', type='http', auth='public',
                methods=['POST'], csrf=False)
    def status(self, **kwargs):
        """Delivery-status callback stub: updates the matching outbound
        message when a provider posts status events."""
        raw = request.httprequest.get_data()
        body = json.loads(raw.decode('utf-8')) if raw else kwargs or {}
        phone = body.get('phone')
        state = body.get('state')
        if state in ('delivered', 'failed') and phone:
            message = request.env['rcloud.whatsapp.message'].sudo().search(
                [('phone', '=', phone), ('direction', '=', 'out'),
                 ('state', '=', 'sent')], limit=1)
            if message:
                message.state = state
        return self._json({'status': 'ok'})
