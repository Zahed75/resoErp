import base64

from unittest.mock import patch, Mock

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.l10n_de_reports.tests.test_tax_report import GermanTaxReportTest

REQUESTS_POST = 'odoo.addons.l10n_de_reports_elster.models.account_return.requests.post'


def _mock_post_success(*args, **kwargs):
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {
        'transfer_ticket': 'ET-2019-11-00001234',
        'hints': [{'field': 'Kz81', 'message': 'Value accepted'}],
        'pdf_confirmation': base64.b64encode(b'%PDF-1.4 fake pdf content').decode(),
    }
    return resp


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestElsterSubmission(GermanTaxReportTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write({
            'street': 'Musterstraße 1',
            'zip': '99099',
            'city': 'Erfurt',
            'phone': '+49 361 1234567',
            'email': 'buchhaltung@test.de',
        })
        cls.de_return_type = cls.env.ref('l10n_de_reports.de_tax_return_type')
        cls.tax_return = cls.env['account.return'].create({
            'name': 'UStVA November 2019',
            'date_from': '2019-11-01',
            'date_to': '2019-11-30',
            'type_id': cls.de_return_type.id,
            'company_id': cls.company.id,
        })

    @freeze_time('2019-12-15')
    def test_successful_submission(self):
        with patch(REQUESTS_POST, side_effect=_mock_post_success):
            self.tax_return.action_submit()

        attachment_names = self.tax_return.attachment_ids.mapped('name')
        self.assertTrue(any('Uebertragungsprotokoll' in n for n in attachment_names))
        msg = self.tax_return.message_ids.filtered(lambda m: 'Successfully submitted' in m.body)[0]
        hints = self.tax_return.message_ids.filtered(lambda m: 'Hints' in m.body)[0]
        self.assertIn('ET-2019-11-00001234', msg.body)
        self.assertTrue('Kz81' in hints.body)

    @freeze_time('2019-12-15')
    def test_payload_attachment_reused_submit(self):
        with self.allow_pdf_render():
            self.tax_return.action_validate(bypass_failing_tests=True)

        before_id = self.tax_return.l10n_de_elster_payload_attachment_id.id

        with patch(REQUESTS_POST, side_effect=_mock_post_success):
            self.tax_return._l10n_de_reports_elster_action_submit()

        after_id = self.tax_return.l10n_de_elster_payload_attachment_id.id
        self.assertEqual(before_id, after_id)
