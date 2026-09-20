# -*- coding: utf-8 -*-
from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _create_document(self, vals):
        """Hook called by the documents app when an attachment is linked to a
        record (on attachment create and on res_model/res_id changes).

        The base implementation only handles models inheriting from
        documents.mixin; rcloud.kyc.record does not, so bridge the KYC case
        here: mirror the attachment into the Documents app, in the dedicated
        "KYC Records" folder, linked back to the KYC record.
        """
        created = super()._create_document(vals)
        if created or self.env.context.get('no_document'):
            return created
        if vals.get('res_model') != 'rcloud.kyc.record' or not vals.get('res_id'):
            return created
        return bool(self._sync_kyc_documents()) or created

    def _sync_kyc_documents(self):
        """Create a documents.document in the KYC folder for every attachment
        in self that is linked to a KYC record and doesn't have a document
        yet. Attachments linked through the record's many2many without
        res_model/res_id are resolved through the relation table, and their
        res_model/res_id is backfilled so the link is consistent everywhere.

        Safe to run repeatedly: existing documents (matched by attachment_id)
        are never duplicated.
        """
        Document = self.env['documents.document'].sudo()
        folder = self.env.ref(
            'rcloud_kyc.kyc_documents_folder', raise_if_not_found=False)
        if not folder or not self:
            return Document

        existing = {
            document.attachment_id.id
            for document in Document.search([('attachment_id', 'in', self.ids)])
        }
        unresolved = self.filtered(
            lambda a: not a.res_id and a.id not in existing)
        resolved = {}
        if unresolved:
            self.env.cr.execute(
                'SELECT attachment_id, kyc_record_id '
                'FROM rcloud_kyc_record_attachment_rel '
                'WHERE attachment_id IN %s',
                (tuple(unresolved.ids),))
            resolved = dict(self.env.cr.fetchall())

        KycRecord = self.env['rcloud.kyc.record'].sudo()
        vals_list = []
        to_backfill = {}
        for attachment in self:
            if attachment.id in existing or attachment.res_field:
                continue
            kyc_id = attachment.res_id or resolved.get(attachment.id)
            if not kyc_id:
                continue
            kyc_record = KycRecord.browse(kyc_id).exists()
            if not kyc_record:
                continue
            if not attachment.res_id:
                to_backfill[attachment] = kyc_record
            vals_list.append({
                'name': attachment.name,
                'attachment_id': attachment.id,
                'folder_id': folder.id,
                'owner_id': attachment.create_uid.id,
                'partner_id': kyc_record.partner_id.id,
                'res_model': 'rcloud.kyc.record',
                'res_id': kyc_record.id,
            })
        documents = Document.create(vals_list) if vals_list else Document
        # Give attachments uploaded through the many2many widget (created
        # without res_model/res_id) a proper link to their KYC record; the
        # documents write hook re-enters _sync_kyc_documents but the document
        # now exists, so nothing is duplicated.
        for attachment, kyc_record in to_backfill.items():
            attachment.sudo().write({
                'res_model': 'rcloud.kyc.record',
                'res_id': kyc_record.id,
            })
        return documents
