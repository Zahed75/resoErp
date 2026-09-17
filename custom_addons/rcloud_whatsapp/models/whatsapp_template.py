# -*- coding: utf-8 -*-
import re

from odoo import fields, models, _


class RcloudWhatsappTemplate(models.Model):
    """A message body with qweb-lite {{placeholders}}. render_for()
    substitutes the standard keys and any extra values passed in."""

    _name = 'rcloud.whatsapp.template'
    _description = 'WhatsApp Template'
    _order = 'key, id'

    name = fields.Char(required=True)
    key = fields.Selection([
        ('booking_confirmed', 'Booking Confirmed'),
        ('pre_arrival', 'Pre-Arrival'),
        ('check_in_ready', 'Check-In Ready'),
        ('checkout_summary', 'Checkout Summary'),
        ('feedback', 'Feedback'),
        ('distribution_statement', 'Distribution Statement'),
        ('announcement', 'Announcement'),
    ], required=True)
    body = fields.Text(
        required=True,
        help='Placeholders: {{guest}}, {{ref}}, {{amount}} and any extra '
             'values passed to render_for().')
    language = fields.Char(
        string='Language', default='en',
        help='ISO language code, e.g. en, bn')

    _key_lang_uniq = models.Constraint(
        'unique(key, language)',
        'A template key can only exist once per language.')

    PLACEHOLDER_RE = re.compile(r'\{\{\s*(\w+)\s*\}\}')

    def render_for(self, record=None, **values):
        """Substitute {{placeholders}} against the record and extra values.

        Standard keys resolved from the record: guest (name), ref (record
        name), amount (amount_total formatted when present).
        """
        self.ensure_one()
        context = dict(values)
        if record is not None:
            context.setdefault('guest', record.display_name)
            context.setdefault('ref', record.name if
                               'name' in record._fields else str(record.id))
            if 'amount_total' in record._fields and record.amount_total:
                context.setdefault(
                    'amount',
                    '{:,.2f}'.format(record.amount_total))
        return self.PLACEHOLDER_RE.sub(
            lambda m: str(context.get(m.group(1), m.group(0))),
            self.body)
