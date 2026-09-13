# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoWhatsAppChatbotRule(models.Model):
    _name = 'reso.whatsapp.chatbot.rule'
    _description = 'Reso WhatsApp Chatbot & FAQ Automation Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name / Topic', required=True)
    sequence = fields.Integer(string='Priority Sequence', default=10)
    trigger_keywords = fields.Char(
        string='Trigger Keywords', required=True,
        help="Comma separated keywords, e.g.: checkin, check-in, arrival time, timing")
    response_template = fields.Text(string='Automated Response', required=True)
    category = fields.Selection([
        ('general', 'General FAQ'),
        ('booking', 'Booking & Availability'),
        ('amenities', 'Resort Amenities'),
        ('ownership', 'Fractional Ownership'),
        ('location', 'Location & Directions'),
    ], string='Category', default='general')
    require_human_handoff = fields.Boolean(string='Flag for Front Desk Handoff', default=False)
    active = fields.Boolean(string='Active', default=True)

    def match_message(self, message_text):
        """Matches incoming message text against keywords."""
        if not message_text or not self.trigger_keywords:
            return False
        keywords = [k.strip().lower() for k in self.trigger_keywords.split(',')]
        msg_lower = message_text.lower()
        return any(k in msg_lower for k in keywords if k)
