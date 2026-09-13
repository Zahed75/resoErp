# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoDocument(models.Model):
    _name = 'reso.document'
    _description = 'Reso Guest & Investor Document Management'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Document Title', required=True, tracking=True)
    document_type = fields.Selection([
        ('passport', 'Passport / ID / NID'),
        ('kyc', 'KYC Compliance File'),
        ('contract', 'Stay / Lease Contract'),
        ('share_cert', 'Share Certificate'),
        ('legal', 'Legal Deed / Ownership Doc'),
        ('other', 'Other Document'),
    ], string='Document Category', default='kyc', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Guest / Investor', required=True, tracking=True)
    booking_id = fields.Many2one('reso.booking', string='Related Booking')
    property_id = fields.Many2one('reso.property', string='Property')
    attachment_ids = fields.Many2many('ir.attachment', string='Files / Attachments')

    expiry_date = fields.Date(string='Document Expiry Date')
    is_verified = fields.Boolean(string='Verified & Compliant', default=False, tracking=True)
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verified_date = fields.Datetime(string='Verified On', readonly=True)

    note = fields.Text(string='Internal Notes')

    def action_verify(self):
        for doc in self:
            doc.write({
                'is_verified': True,
                'verified_by': self.env.uid,
                'verified_date': fields.Datetime.now(),
            })

    def action_unverify(self):
        for doc in self:
            doc.write({
                'is_verified': False,
                'verified_by': False,
                'verified_date': False,
            })
