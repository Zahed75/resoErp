# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _uninstall_blackbox_condition(self):
        res = super()._uninstall_blackbox_condition()
        signed_order_count_v2 = self.env['pos.order'].search_count([('l10n_be_short_signature', '!=', False)], limit=1)
        self.env['pos.config']._migrate_blackbox_data_v1_to_v2()
        return res or signed_order_count_v2 > 0
