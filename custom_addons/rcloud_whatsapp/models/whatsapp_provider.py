# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudWhatsappProviderInterface(models.AbstractModel):
    """WhatsApp transport abstraction. Swap the implementation per
    database with the rcloud.whatsapp.provider ir.config_parameter."""

    _name = 'rcloud.whatsapp.provider'
    _description = 'WhatsApp Provider Interface'

    def send(self, phone, body, partner=None, template=None):
        """Deliver `body` to `phone`. Must return the created
        rcloud.whatsapp.message record (or False)."""
        raise NotImplementedError()


class RcloudWhatsappProviderLog(models.Model):
    """Default provider: logs the message locally, delivers nothing.
    This is the safe fallback until a real BSP/360dialog/Meta provider
    is configured."""

    _name = 'rcloud.whatsapp.provider.log'
    _description = 'WhatsApp Log Provider'
    _inherit = 'rcloud.whatsapp.provider'

    def send(self, phone, body, partner=None, template=None):
        return self.env['rcloud.whatsapp.message'].create({
            'partner_id': partner.id if partner else False,
            'phone': phone,
            'direction': 'out',
            'body': body,
            'template_id': template.id if template else False,
            'state': 'sent',
        })
