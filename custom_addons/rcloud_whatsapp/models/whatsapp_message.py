# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class RcloudWhatsappMessage(models.Model):
    """One WhatsApp message, inbound or outbound, logged on the partner
    chatter. Outbound sending always goes through the configured
    provider."""

    _name = 'rcloud.whatsapp.message'
    _description = 'WhatsApp Message'
    _order = 'id desc'

    partner_id = fields.Many2one(
        'res.partner', string='Guest', ondelete='set null', index=True)
    phone = fields.Char(required=True)
    direction = fields.Selection([
        ('in', 'Inbound'), ('out', 'Outbound')], required=True)
    body = fields.Text(required=True)
    template_id = fields.Many2one('rcloud.whatsapp.template', readonly=True)
    state = fields.Selection([
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], default='sent', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        for message in messages:
            if message.partner_id and message.direction == 'out':
                message.partner_id.message_post(
                    body=_('[WhatsApp] %s') % message.body)
        return messages

    @api.model
    def send_template(self, key, partner, **values):
        """Render template `key` for `partner` and send it through the
        configured provider. Returns the message record, or False when
        the template is missing or the guest opted out."""
        Template = self.env['rcloud.whatsapp.template'].sudo()
        template = Template.search([('key', '=', key)], limit=1)
        if not template:
            return False
        if partner.whatsapp_opt_out:
            return False
        body = template.render_for(record=partner, **values)
        provider_name = self.env['ir.config_parameter'].sudo().get_param(
            'rcloud.whatsapp.provider', 'rcloud.whatsapp.provider.log')
        provider = self.env[provider_name].sudo()
        return provider.send(
            partner.whatsapp_number or partner.phone or
            getattr(partner, 'mobile', None),
            body, partner=partner, template=template)
