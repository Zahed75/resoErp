# -*- coding: utf-8 -*-
from odoo import fields, models


class RcloudProperty(models.Model):
    _inherit = 'rcloud.property'

    kyc_required = fields.Boolean(
        string='KYC Required',
        help='Refuse check-in until the guest has a verified KYC record.')
