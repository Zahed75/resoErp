# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudWhatsappChatbotRule(models.Model):
    """Keyword-triggered auto replies, matched in sequence order."""

    _name = 'rcloud.whatsapp.chatbot.rule'
    _description = 'WhatsApp Chatbot Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    trigger_keywords = fields.Char(
        required=True,
        help='Comma separated keywords, e.g.: checkin, check-in, wifi')
    response_template = fields.Text(required=True)
    active = fields.Boolean(default=True)

    def match_message(self, message_text):
        if not message_text or not self.trigger_keywords:
            return False
        keywords = [k.strip().lower() for k in self.trigger_keywords.split(',')]
        text = message_text.lower()
        return any(k and k in text for k in keywords)
