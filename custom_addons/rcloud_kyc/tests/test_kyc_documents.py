# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKycDocuments(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = cls.env.ref('rcloud_kyc.kyc_documents_folder')
        cls.guest = cls.env['res.partner'].create({
            'name': 'KYC Documents Guest'})
        cls.record = cls.env['rcloud.kyc.record'].create({
            'partner_id': cls.guest.id,
            'doc_type': 'passport',
            'doc_number': 'P123456789',
        })

    def _attach(self, name='passport.pdf'):
        return self.env['ir.attachment'].create({
            'name': name,
            'datas': 'aGVsbG8=',
            'res_model': 'rcloud.kyc.record',
            'res_id': self.record.id,
        })

    def test_attachment_creates_document_in_kyc_folder(self):
        attachment = self._attach()
        document = self.env['documents.document'].sudo().search([
            ('attachment_id', '=', attachment.id)])
        self.assertEqual(len(document), 1)
        self.assertEqual(document.folder_id, self.folder)
        self.assertEqual(document.res_model, 'rcloud.kyc.record')
        self.assertEqual(document.res_id, self.record.id)
        self.assertEqual(document.partner_id, self.guest)
        # The superuser cannot own documents (Odoo clears owner_id); any
        # other creator becomes the document owner.
        if attachment.create_uid.id == 1:
            self.assertFalse(document.owner_id)
        else:
            self.assertEqual(document.owner_id, attachment.create_uid)

    def test_attachment_via_widget_m2m_is_synced(self):
        """Attachments uploaded through the form's many2many widget have no
        res_id; linking them to the record must still create the document."""
        attachment = self.env['ir.attachment'].create({
            'name': 'nid_scan.pdf',
            'datas': 'aGVsbG8=',
        })
        self.record.attachment_ids = [(4, attachment.id)]
        document = self.env['documents.document'].sudo().search([
            ('attachment_id', '=', attachment.id)])
        self.assertEqual(len(document), 1)
        self.assertEqual(document.folder_id, self.folder)
        self.assertEqual(document.res_model, 'rcloud.kyc.record')
        self.assertEqual(document.res_id, self.record.id)
        # The attachment itself is backfilled so it stays consistent.
        self.assertEqual(attachment.res_model, 'rcloud.kyc.record')
        self.assertEqual(attachment.res_id, self.record.id)

    def test_sync_twice_does_not_duplicate(self):
        attachment = self._attach()
        self.record.attachment_ids = [(4, attachment.id)]
        self.env['rcloud.kyc.record'].action_sync_documents()
        self.env['rcloud.kyc.record'].action_sync_documents()
        documents = self.env['documents.document'].sudo().search([
            ('folder_id', '=', self.folder.id),
            ('res_model', '=', 'rcloud.kyc.record'),
            ('res_id', '=', self.record.id),
        ])
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents.attachment_id, attachment)
