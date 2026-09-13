# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_bg_saft_related_company_ids = fields.Many2many(
        comodel_name='res.company',
        relation='l10n_bg_saft_relations',
        string='Related companies (BG SAF-T)',
        help='All the related companies according to §1, item 3 of the DR of DOPK. This is used for SAF-T report export.',
    )
