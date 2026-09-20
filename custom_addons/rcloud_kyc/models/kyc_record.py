# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RcloudKycRecord(models.Model):
    """One identity document per guest. Verification is permissioned and
    the raw document number never reaches screens that plain hotel staff
    can open."""

    _name = 'rcloud.kyc.record'
    _description = 'KYC Record'
    _order = 'id desc'
    _inherit = ['mail.thread']

    partner_id = fields.Many2one(
        'res.partner', string='Guest', required=True,
        ondelete='restrict', index=True)
    property_id = fields.Many2one('rcloud.property', ondelete='restrict')
    doc_type = fields.Selection([
        ('passport', 'Passport'),
        ('nid', 'National ID'),
        ('driving_licence', 'Driving Licence'),
        ('visa', 'Visa'),
    ], required=True)
    doc_number = fields.Char(
        required=True, groups='rcloud_kyc.group_kyc_officer,'
                              'rcloud_base.group_hotel_manager')
    doc_number_display = fields.Char(
        string='Document Number',
        compute='_compute_doc_number_display',
        help='Masked document number (first two and last two characters).')
    issuing_country = fields.Many2one('res.country')
    issue_date = fields.Date()
    expiry_date = fields.Date()
    attachment_ids = fields.Many2many(
        'ir.attachment', 'rcloud_kyc_record_attachment_rel',
        'kyc_record_id', 'attachment_id', string='Documents')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True, tracking=True)
    verified_by = fields.Many2one('res.users', readonly=True, copy=False)
    verified_on = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Char(copy=False)

    # At most one non-rejected record per partner and document type is
    # enforced by _check_single_open_record (a Python constraint, so the
    # friendly ValidationError fires instead of a raw IntegrityError).

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.attachment_ids._sync_kyc_documents()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self.attachment_ids._sync_kyc_documents()
        return res

    @api.model
    def action_sync_documents(self):
        """Backfill entry point: mirror every attachment linked to a KYC
        record (via res_model/res_id or the attachment_ids relation) into the
        Documents app. Safe to run repeatedly."""
        Attachment = self.env['ir.attachment'].sudo()
        self.env.cr.execute(
            'SELECT attachment_id FROM rcloud_kyc_record_attachment_rel')
        rel_ids = [row[0] for row in self.env.cr.fetchall()]
        attachments = Attachment.search([
            ('res_model', '=', 'rcloud.kyc.record')]) | Attachment.browse(rel_ids)
        return attachments._sync_kyc_documents()

    @api.constrains('partner_id', 'doc_type', 'state')
    def _check_single_open_record(self):
        """Friendly guard mirroring the partial unique index: at most one
        non-rejected record per partner and document type."""
        for rec in self:
            if rec.state == 'rejected':
                continue
            dup = self.search([
                ('id', '!=', rec.id),
                ('partner_id', '=', rec.partner_id.id),
                ('doc_type', '=', rec.doc_type),
                ('state', '!=', 'rejected'),
            ], limit=1)
            if dup:
                raise ValidationError(_(
                    '%s already has an open %s record.') % (
                    rec.partner_id.name, rec.doc_type))

    @api.depends('doc_number')
    def _compute_doc_number_display(self):
        for rec in self:
            number = rec.doc_number or ''
            if len(number) > 4:
                rec.doc_number_display = number[:2] + '****' + number[-2:]
            elif number:
                rec.doc_number_display = '****'
            else:
                rec.doc_number_display = ''

    def action_submit(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Only pending records can be submitted.'))
            rec.state = 'submitted'
            rec.message_post(body=_('KYC record submitted for verification.'))

    def action_verify(self):
        if not self.env.user.has_group('rcloud_kyc.group_kyc_officer'):
            raise UserError(
                _('Only KYC officers can verify records.'))
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted records can be verified.'))
            rec.write({
                'state': 'verified',
                'verified_by': self.env.user.id,
                'verified_on': fields.Datetime.now(),
                'rejection_reason': False,
            })
            rec.message_post(body=_('KYC record verified.'))

    def action_reject(self):
        if not self.env.user.has_group('rcloud_kyc.group_kyc_officer'):
            raise UserError(
                _('Only KYC officers can reject records.'))
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted records can be rejected.'))
            if not rec.rejection_reason:
                raise ValidationError(
                    _('A rejection reason is required.'))
            rec.state = 'rejected'
            rec.message_post(body=_(
                'KYC record rejected: %s') % rec.rejection_reason)

    def _anonymize(self):
        """GDPR erasure: drop the evidence and blank the identifiers."""
        for rec in self:
            rec.attachment_ids.unlink()
            rec.write({
                'doc_number': 'XXXX',
                'issuing_country': False,
                'issue_date': False,
                'expiry_date': False,
                'rejection_reason': False,
                'state': 'rejected',
            })
