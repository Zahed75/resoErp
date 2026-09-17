# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_opt_in = fields.Boolean(
        string='WhatsApp Opt-In', default=False,
        help='Guest consented to receiving WhatsApp messages.')
    whatsapp_consent_date = fields.Datetime(
        string='WhatsApp Consent Date', readonly=True)
    whatsapp_opt_out = fields.Boolean(
        string='WhatsApp Opted Out', default=False,
        help='Set when the guest texts STOP; automated sends are skipped.')
    whatsapp_number = fields.Char(string='WhatsApp Number')

    def write(self, vals):
        res = super().write(vals)
        if vals.get('whatsapp_opt_in'):
            self.filtered(lambda p: not p.whatsapp_consent_date).write(
                {'whatsapp_consent_date': fields.Datetime.now()})
        return res
