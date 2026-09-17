# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RcloudPropertyMixin(models.AbstractModel):
    """Drop-in multi-property dimension.

    Any model inheriting this mixin gains:
      * a required, indexed property_id
      * related company_id (stored) for record-rule partitioning
      * constraint: the record's company must match the property's company
      * helper to stamp the property analytic account on journal items
    """

    _name = 'rcloud.property.mixin'
    _description = 'Property Dimension Mixin'

    property_id = fields.Many2one(
        'rcloud.property', required=True, ondelete='restrict', index=True)
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')

    @api.constrains('property_id', 'company_id')
    def _check_property_company(self):
        for rec in self:
            if rec.property_id.company_id and rec.company_id and \
                    rec.property_id.company_id != rec.company_id:
                raise ValidationError(
                    _('The record must belong to the property\'s company.'))

    def _analytic_distribution(self):
        """Analytic distribution dict {account_id: 100} for journal items."""
        self.ensure_one()
        account = self.property_id.analytic_account_id
        return {str(account.id): 100} if account else {}
