from datetime import timedelta
from freezegun import freeze_time
from psycopg2.errors import ForeignKeyViolation

from odoo.addons.documents_sign.tests.test_documents import TestCaseDocumentsBridgeSign
from odoo.tools import mute_logger


class TestSignedDocument(TestCaseDocumentsBridgeSign):
    def setUp(cls):
        super().setUp()
        partner = cls.env["res.partner"]
        user = cls.env["res.users"].create(
            {
                "name": "test_sign_owner_",
                "login": "test_sign_owner@ex.com",
                "email": "test_sign_owner@ex.com",
            }
        )
        sign_request = cls.create_sign_request_1_role(user.partner_id, partner)
        sign_document = cls.document_3
        sign_request.completed_document_attachment_ids = [(4, cls.attachment.id)]

        cls.trash_doc, cls.signed_document_pdf, cls.sign_doc = cls.env["documents.document"].create([
            {
                "name": "trash_doc",
                "attachment_id": cls.attachment.copy().id,
                "folder_id": cls.folder_a_a.id,
                "active": False,
                "res_model": False,
            }, {
                "name": "signed document",
                "folder_id": cls.folder_a_a.id,
                "res_model": sign_request._name,
                "res_id": sign_request.id,
                "active": False,
                "attachment_id": cls.attachment.id,
            }, {
                "name": "sign document",
                "attachment_id": sign_document.attachment_id.id,
                "folder_id": cls.folder_a_a.id,
                "res_model": sign_document._name,
                "res_id": sign_document.id,
                "active": False,
            }
        ])

    def test_gc_clear_bin(self):
        """ Ensure that old, auto-deletable (in the trash) documents linked to sign requests and sign documents are not
        deleted by the garbage collector.
        """

        self.assertFalse(self.sign_doc.active)
        self.assertFalse(self.signed_document_pdf.active)
        self.assertFalse(self.trash_doc.active)
        documents_deletion_date = self.signed_document_pdf.write_date + timedelta(days=self.signed_document_pdf.get_deletion_delay(), seconds=30)
        with freeze_time(documents_deletion_date):
            self.env["documents.document"]._gc_clear_bin()

        self.assertTrue(self.sign_doc.exists(), "sign document should not be deleted after gc_clear_bin")
        self.assertTrue(self.signed_document_pdf.exists(), "signed document should not be deleted after gc_clear_bin")
        self.assertFalse(self.trash_doc.exists(), "trash document should be deleted after gc_clear_bin")

    def test_gc_clear_bin_shared_attachment(self):
        """ A trashed document whose res_model is not a sign model but whose
        attachment is held by a sign.document must survive the GC. Unlinking it
        would abort the whole autovacuum on the ondelete='restrict' foreign key.
        """
        bare_attachment = self.env["ir.attachment"].create({
            "name": "shared.pdf",
            "datas": self.attachment.datas,
            "res_model": False,
            "res_id": False,
        })
        sign_document = self.env["sign.document"].create({
            "attachment_id": bare_attachment.id,
            "template_id": self.template_no_item.id,
        })
        shared_doc = self.env["documents.document"].create({
            "name": "shared attachment doc",
            "folder_id": self.folder_a_a.id,
            "attachment_id": sign_document.attachment_id.id,
            "res_model": False,
            "active": False,
        })
        self.assertFalse(shared_doc.active)
        deletion_date = shared_doc.write_date + timedelta(days=shared_doc.get_deletion_delay(), seconds=30)
        with freeze_time(deletion_date):
            self.env["documents.document"]._gc_clear_bin()

        self.assertTrue(shared_doc.exists(), "a document sharing a sign.document attachment should survive gc_clear_bin")
        self.assertTrue(sign_document.exists(), "the sign document should be untouched by gc_clear_bin")

    @mute_logger("odoo.models.unlink")
    def test_signed_document_unlink(self):
        """ Test that attempting to directly unlink a sign or signed document raises a foreign key
        constraint error due to its link with a sign document or sign request.
        """
        self.assertFalse(self.sign_doc.active)
        self.assertFalse(self.signed_document_pdf.active)

        with (self.assertRaises(ForeignKeyViolation), mute_logger("odoo.sql_db")):
            self.sign_doc.unlink()
        with (self.assertRaises(ForeignKeyViolation), mute_logger("odoo.sql_db")):
            self.signed_document_pdf.unlink()
