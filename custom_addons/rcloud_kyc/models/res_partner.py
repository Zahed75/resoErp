# -*- coding: utf-8 -*-
import base64
import json

from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    kyc_record_ids = fields.One2many(
        'rcloud.kyc.record', 'partner_id', string='KYC Records')

    def action_gdpr_export(self):
        """Bundle the personal data we hold on the partner into a JSON
        attachment for data-portability requests."""
        self.ensure_one()
        data = {
            'partner': {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'phone': self.phone,
                'street': self.street,
                'city': self.city,
                'country': self.country_id.code,
            },
            'kyc_records': [{
                'id': rec.id,
                'doc_type': rec.doc_type,
                'doc_number': rec.doc_number,
                'issuing_country': rec.issuing_country.code,
                'issue_date': str(rec.issue_date) if rec.issue_date else None,
                'expiry_date': str(rec.expiry_date) if rec.expiry_date else None,
                'state': rec.state,
                'verified_on': str(rec.verified_on) if rec.verified_on else None,
            } for rec in self.kyc_record_ids],
        }
        attachment = self.env['ir.attachment'].create({
            'name': 'gdpr_export_%d.json' % self.id,
            'type': 'binary',
            'datas': base64.b64encode(
                json.dumps(data, indent=2, default=str).encode('utf-8')),
            'res_model': 'res.partner',
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_gdpr_erase(self):
        """Right-to-be-forgotten: anonymize the partner and wipe the KYC
        evidence attached to them. Irreversible by design."""
        for partner in self:
            partner.kyc_record_ids._anonymize()
            partner.write({
                'name': 'Erased',
                'email': False,
                'phone': False,
                'street': False,
                'street2': False,
                'city': False,
                'comment': False,
            })
            partner.message_post(body=_(
                'Personal data erased (GDPR erasure request).'))
