# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class RcloudReservation(models.Model):
    _inherit = 'rcloud.reservation'

    def _kyc_verified(self):
        self.ensure_one()
        return bool(self.env['rcloud.kyc.record'].sudo().search_count([
            ('partner_id', '=', self.guest_id.id),
            ('state', '=', 'verified'),
        ]))

    def action_check_in(self):
        """Guard added on top of the PMS transition: properties flagged
        kyc_required refuse check-in without a verified KYC record."""
        for res in self:
            if res.property_id.kyc_required and not res._kyc_verified():
                raise UserError(_(
                    'KYC verification required before check-in for %s.') %
                    res.guest_id.name)
        return super().action_check_in()
