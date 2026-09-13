from odoo import api, models, fields


class PosBlackboxLogDevice(models.Model):
    _name = 'pos.blackbox.log.device'
    _description = 'POS Blackbox Log Device'

    device = fields.Char(string='Device Identifier', required=True)
    _device_unique = models.UniqueIndex('(device)')

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            if vals.get('device'):
                existing = self.search([('device', '=', vals['device'])], limit=1)
                if existing:
                    records |= existing
                else:
                    records |= super().create([vals])
        return records

    @api.model
    def log_device(self, config_id, device):
        """Authorize (and register) the physical device opening a POS

        Ensure that a device already linked to a blackbox POS may no longer open a non-blackbox POS.
        ``device`` is an identifier persisted in the browser's local storage and passed when opening POS UI.

        - Config with a blackbox -> always authorized
          The device is registered only once the config has produced at least one signed order,
          so the very first opening (before any sale) does not yet lock  the device
        - Config without a blackbox -> authorized only if the device has never been registered by a blackbox POS.

        :param int config_id:
        :param str device: identifier of the physical device

        :return: "True" if allowed, "False" if blocked
        """
        if not device:
            return False

        config = self.env['pos.config'].browse(config_id)

        signed_order_count = self.env['pos.order'].search_count([
            ('config_id', '=', config_id),
            ('l10n_be_short_signature', '!=', False),
        ], limit=1)
        if config.l10n_be_blackbox_be_id:
            if signed_order_count:
                self.create({'device': device})
            return True
        return not self.search_count([('device', '=', device)], limit=1)
