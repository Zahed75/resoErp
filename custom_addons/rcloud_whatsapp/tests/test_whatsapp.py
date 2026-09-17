# -*- coding: utf-8 -*-
import json

from odoo.tests import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWhatsappTemplate(TransactionCase):

    def test_render_for(self):
        template = self.env['rcloud.whatsapp.template'].create({
            'name': 'Test', 'key': 'announcement', 'language': 'zz',
            'body': 'Dear {{guest}}, ref {{ref}}, amount {{amount}} '
                    '{{extra}} {{unknown}}',
        })
        partner = self.env['res.partner'].create({'name': 'Jane Guest'})
        body = template.render_for(
            record=partner, ref='RSV/001', amount='1,000.00', extra='yes')
        self.assertEqual(
            body, 'Dear Jane Guest, ref RSV/001, amount 1,000.00 yes '
                  '{{unknown}}')

    def test_render_for_record_amount(self):
        template = self.env['rcloud.whatsapp.template'].create({
            'name': 'Test', 'key': 'checkout_summary', 'language': 'zz',
            'body': 'Total {{amount}}',
        })
        fake = self.env['res.partner'].create({'name': 'X'})
        # No amount on the record and none passed: placeholder is kept.
        body = template.render_for(record=fake)
        self.assertEqual(body, 'Total {{amount}}')
        # Explicit values always win.
        body = template.render_for(record=fake, amount='42.00')
        self.assertEqual(body, 'Total 42.00')


@tagged('post_install', '-at_install')
class TestWhatsappMessage(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'WA Guest', 'phone': '+1555000111',
        })

    def test_send_template_respects_opt_out(self):
        result = self.env['rcloud.whatsapp.message'].send_template(
            'booking_confirmed', self.partner)
        self.assertTrue(result)
        self.assertEqual(result.direction, 'out')
        self.assertIn(self.partner.name, result.body)
        self.assertTrue(
            self.env['mail.message'].search_count([
                ('model', '=', 'res.partner'),
                ('res_id', '=', self.partner.id),
            ]))

        self.partner.whatsapp_opt_out = True
        result = self.env['rcloud.whatsapp.message'].send_template(
            'booking_confirmed', self.partner)
        self.assertFalse(result)

    def test_send_template_missing_template(self):
        self.env['rcloud.whatsapp.template'].search([
            ('key', '=', 'announcement')]).unlink()
        result = self.env['rcloud.whatsapp.message'].send_template(
            'announcement', self.partner)
        self.assertFalse(result)

    def test_keyword_matching(self):
        Rule = self.env['rcloud.whatsapp.chatbot.rule']
        rule = Rule.create({
            'name': 'WiFi', 'trigger_keywords': 'wifi, password, internet',
            'response_template': 'WiFi password: resort2026',
        })
        self.assertTrue(rule.match_message('What is the wifi password?'))
        self.assertTrue(rule.match_message('INTERNET please'))
        self.assertFalse(rule.match_message('late checkout'))
        self.assertFalse(rule.match_message(''))


@tagged('post_install', '-at_install')
class TestWhatsappWebhook(HttpCase):

    def test_webhook_bot_reply_and_logging(self):
        self.env['rcloud.whatsapp.chatbot.rule'].sudo().create({
            'name': 'Checkin', 'trigger_keywords': 'checkin',
            'response_template': 'Check-in starts at 2 PM.',
        })
        response = self.url_open(
            '/rcloud/whatsapp/webhook',
            data=json.dumps({
                'phone': '+1555000222', 'message': 'checkin time?'}),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['bot_reply'], 'Check-in starts at 2 PM.')
        partner = self.env['res.partner'].sudo().search([
            ('whatsapp_number', '=', '+1555000222')])
        self.assertTrue(partner)
        messages = self.env['rcloud.whatsapp.message'].sudo().search([
            ('partner_id', '=', partner.id)])
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            messages.mapped('direction'), ['out', 'in'])

    def test_webhook_stop_opt_out(self):
        partner = self.env['res.partner'].sudo().create({
            'name': 'WA Stop', 'whatsapp_number': '+1555000333',
        })
        response = self.url_open(
            '/rcloud/whatsapp/webhook',
            data=json.dumps({'phone': '+1555000333', 'message': 'STOP'}),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(partner.whatsapp_opt_out)
        self.assertFalse(partner.whatsapp_opt_in)

    def test_status_callback(self):
        response = self.url_open(
            '/rcloud/whatsapp/status',
            data=json.dumps({'phone': '+1555000444', 'state': 'delivered'}),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
