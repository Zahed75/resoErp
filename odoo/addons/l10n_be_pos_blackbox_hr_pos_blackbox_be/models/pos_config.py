# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import SQL


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _migrate_blackbox_data_v1_to_v2_employee(self):
        self._migrate_hr_employee_insz()

    def _migrate_hr_employee_insz(self):
        """Move pos_blackbox_be.hr_employee insz_or_bis_number into l10n_be_insz_or_bis_number on hr.employee."""

        self.env.execute_query(SQL("""
            UPDATE hr_employee
            SET l10n_be_insz_or_bis_number = insz_or_bis_number
            WHERE insz_or_bis_number IS NOT NULL
            AND insz_or_bis_number != ''
            AND (l10n_be_insz_or_bis_number IS NULL OR l10n_be_insz_or_bis_number = '')
            """)
        )
