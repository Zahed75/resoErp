from unittest.mock import patch

from odoo.tests import tagged
from .common import TestPeEdiCommon

VALID_CDR = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
<ar:ApplicationResponse
    xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ResponseCode>0</cbc:ResponseCode>
    <cbc:Description>The invoice has been accepted</cbc:Description>
</ar:ApplicationResponse>
"""

INVALID_CDR = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
<ar:ApplicationResponse
    xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ResponseCode>2800</cbc:ResponseCode>
    <cbc:Description>The invoice has been rejected</cbc:Description>
</ar:ApplicationResponse>
"""


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestEdiRetrieveCdr(TestPeEdiCommon):
    """ Check that _l10n_pe_edi_retrieve_cdr() only marks a result retryable ('warning') when we
    don't have a definitive answer from SUNAT yet, and keeps it blocking ('error') once SUNAT has
    definitively rejected the document, so the EDI cron doesn't retry forever on a lost cause. """

    def _retrieve_cdr(self, get_status_cdr_return_value):
        with patch(
            'odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_get_status_cdr_sunat_service',
            return_value=get_status_cdr_return_value,
        ):
            return self.edi_format._l10n_pe_edi_retrieve_cdr(
                'sunat', self.company_data['company'], {'serie': 'F001', 'folio': '1'}, '01')

    def test_transient_connection_error_is_a_warning(self):
        """ The underlying service couldn't even reach SUNAT: worth retrying maybe a timout"""
        res = self._retrieve_cdr({'error': 'connection timed out', 'blocking_level': 'warning'})
        self.assertEqual(res['blocking_level'], 'warning')

    def test_cdr_not_yet_available_is_a_warning(self):
        """ SUNAT answered but the CDR isn't generated yet: still worth retrying. """
        res = self._retrieve_cdr({'error': 'CDR not found yet', 'blocking_level': 'warning'})
        self.assertEqual(res['blocking_level'], 'warning')

    def test_soap_fault_without_blocking_level_defaults_to_error(self):
        """ SOAP fault from SUNAT with no explicit blocking_level must default to
        blocking ('error'), not be silently treated as retryable. """
        res = self._retrieve_cdr({'error': 'invalid VAT number', 'code': '1034'})
        self.assertEqual(res['blocking_level'], 'error')

    def test_soap_fault_marked_error_stays_error(self):
        res = self._retrieve_cdr({'error': 'invalid VAT number', 'blocking_level': 'error', 'code': '1034'})
        self.assertEqual(res['blocking_level'], 'error')

    def test_unexpected_status_code_is_a_warning(self):
        """ A response without an 'error' key but whose status code isn't the expected 0004
        ('CDR exists') is treated as inconclusive, not a definitive rejection. """
        res = self._retrieve_cdr({'code': '0001', 'status': '0001|In progress'})
        self.assertEqual(res['blocking_level'], 'warning')

    def test_cdr_retrieved_and_valid(self):
        res = self._retrieve_cdr({'code': '0004', 'cdr': VALID_CDR})
        self.assertFalse(res.get('error'))

    def test_cdr_retrieved_but_invalid_is_a_definitive_error(self):
        res = self._retrieve_cdr({'code': '0004', 'cdr': INVALID_CDR})
        self.assertEqual(res['blocking_level'], 'error')
