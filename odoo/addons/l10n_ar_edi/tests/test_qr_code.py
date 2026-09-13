# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ar_edi.tests.common import TestArEdiCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestArEdiQrCode(TestArEdiCommon):

    def test_qr_code_identification_type_without_arca_code(self):
        """ The QR code must be rendered even when the partner's identification
        type has no ARCA code (e.g. the generic "VAT" type on foreign partners
        of export invoices), falling back to tipoDocRec 0 instead of crashing
        with int(None). """
        self.res_partner_barcelona_food.write({
            'l10n_latam_identification_type_id': self.env.ref('l10n_latam_base.it_vat').id,
            'vat': 'ESA12345674',
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.res_partner_barcelona_food.id,
            'journal_id': self.sale_expo_journal_ri.id,
            'l10n_latam_document_type_id': self.document_type['invoice_e'].id,
            'invoice_date': '2026-08-04',
            'invoice_line_ids': [Command.create({'name': 'Test product', 'quantity': 1, 'price_unit': 100.0})],
        })
        invoice.l10n_latam_document_number = '00002-00000001'
        # Simulate an ARCA validated invoice (these values are normally set by the ws)
        invoice.write({
            'l10n_ar_afip_auth_mode': 'CAE',
            'l10n_ar_afip_auth_code': '12345678901234',
        })
        qr_data = json.loads(base64.b64decode(invoice.l10n_ar_afip_qr_code.split('?p=')[1]))
        self.assertEqual(qr_data['tipoDocRec'], 0)
