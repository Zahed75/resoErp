# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_tr_is_current_turkey_citizen = fields.Boolean(compute='_compute_l10n_tr_is_current_turkey_citizen', groups="hr.group_hr_user")
    l10n_tr_is_net_to_gross = fields.Boolean(
        readonly=False,
        related="version_id.l10n_tr_is_net_to_gross",
        inherited=True,
        groups="hr_payroll.group_hr_payroll_user",
    )

    @api.depends("current_version_id.country_id.code", "current_version_id.is_non_resident")
    def _compute_l10n_tr_is_current_turkey_citizen(self):
        for emp in self:
            emp.l10n_tr_is_current_turkey_citizen = (
                emp.current_version_id.country_id.code == "TR"
                and not emp.current_version_id.is_non_resident
            )
