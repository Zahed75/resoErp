from odoo.tests import tagged
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLogDevice(TestFrontendCommon):
    """Unit tests for 'pos.blackbox.log.device.log_device'"""

    @classmethod
    @TestFrontendCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()
        cls.blackbox_be = cls.env['pos.blackbox.be'].sudo().create({
            'fdm_id': 'VCB01002601',
            'display_name': "Blackbox - 123456789",
            'name': "Blackbox - 123456789",
            'local_ip': "0.0.0.0",
        })

        cls.main_pos_config.write({
            'l10n_be_blackbox_be_id': cls.blackbox_be.id,
            'l10n_be_pos_id': 'CDEM0000000001',
            'epson_printer_ip': '127.0.0.1:8069/receipt_receiver',
            'other_devices': True,
            'establishment_number': '8789456149'
        })
        cls.env.user.l10n_be_insz_or_bis_number = '00000000097'
        cls.pos_user.l10n_be_insz_or_bis_number = '00000000097'
        cls.pos_admin.sudo().l10n_be_insz_or_bis_number = '00000000097'
        cls.env.company.write({
            'street': 'Rue de Ramilles 1',
            'vat': 'BE0477472701',
        })

        # A second config without any blackbox, to test the non-fiscal branch.
        cls.non_blackbox_config = cls.main_pos_config.copy({
            'name': 'Non-Blackbox POS',
            'l10n_be_blackbox_be_id': False,
        })

        cls.LogDevice = cls.env['pos.blackbox.log.device']

    def _create_signed_order(self, config):
        """Create a minimally-valid, fiscally-signed order on ``config``."""
        if not config.current_session_id:
            config.with_user(self.pos_user).open_ui()
        return self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': config.current_session_id.id,
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'l10n_be_short_signature': 'ABC123',
        })

    def test_no_device_returns_false(self):
        """No device identifier -> unauthorized (False)"""
        result = self.LogDevice.log_device(self.main_pos_config.id, '')
        self.assertFalse(result)
        self.assertFalse(self.LogDevice.search_count([]))

    def test_blackbox_config_no_signed_order_authorized_not_registered(self):
        """Opening a blackbox POS before its first sale is allowed but the device is not locked yet"""
        result = self.LogDevice.log_device(self.main_pos_config.id, 'device-A')
        self.assertTrue(result)
        self.assertFalse(
            self.LogDevice.search_count([('device', '=', 'device-A')]),
            "Device must not be registered before the first signed order",
        )

    def test_blackbox_config_with_signed_order_registers_device(self):
        """Once a signed order exists, the device is registered and allowed"""
        self._create_signed_order(self.main_pos_config)
        result = self.LogDevice.log_device(self.main_pos_config.id, 'device-B')
        self.assertTrue(result)
        self.assertEqual(
            self.LogDevice.search_count([('device', '=', 'device-B')]), 1,
            "Device must be registered after the first signed order",
        )

    def test_blackbox_config_double_registration(self):
        """Logging the same device twice keeps a single record (unique device)."""
        self._create_signed_order(self.main_pos_config)
        self.assertTrue(self.LogDevice.log_device(self.main_pos_config.id, 'device-C'))
        self.assertTrue(self.LogDevice.log_device(self.main_pos_config.id, 'device-C'))
        self.assertEqual(
            self.LogDevice.search_count([('device', '=', 'device-C')]), 1,
            "A device must never be registered more than once",
        )

    def test_non_blackbox_config_unknown_device_authorized(self):
        """A never-seen device may open a non-fiscal POS"""
        result = self.LogDevice.log_device(self.non_blackbox_config.id, 'device-D')
        self.assertTrue(result)

    def test_device_locked_to_blackbox_after_fiscal_use(self):
        """A device already registered by a blackbox POS is blocked on a non-fiscal POS"""
        self._create_signed_order(self.main_pos_config)
        # The device gets registered while opening the fiscal POS.
        self.assertTrue(self.LogDevice.log_device(self.main_pos_config.id, 'device-F'))
        # It is now rejected on any non-fiscal POS.
        self.assertFalse(self.LogDevice.log_device(self.non_blackbox_config.id, 'device-F'))

    def test_second_device_accessible_after_fiscal_use(self):
        """A device already registered by a blackbox POS is blocked on a non-fiscal POS"""
        second_pos_config = self.main_pos_config.copy({
            'name': 'Second POS',
        })
        self._create_signed_order(self.main_pos_config)
        self.assertTrue(self.LogDevice.log_device(self.main_pos_config.id, 'device-F'))
        self.assertTrue(self.LogDevice.log_device(second_pos_config.id, 'device-F'))
