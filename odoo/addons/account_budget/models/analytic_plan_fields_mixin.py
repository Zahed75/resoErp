# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AnalyticPlanFields(models.AbstractModel):
    _inherit = 'analytic.plan.fields.mixin'

    def _by_shape(self):
        plan_fnames = self._get_plan_fnames()
        return self.grouped(lambda r: tuple(bool(r[fname]) for fname in plan_fnames))
