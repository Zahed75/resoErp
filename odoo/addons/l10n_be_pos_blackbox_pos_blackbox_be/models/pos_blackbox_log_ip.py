# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError


class PosBlackboxLogIp(models.Model):
    _inherit = 'pos.blackbox.log.ip'

    def _log_ip(self, config_id, ip):
        # If the config uses blackbox v2, the config is considered as certified
        try:
            super()._log_ip(config_id, ip)
        except UserError:
            if config_id._uses_blackbox_v2():
                return
            raise
