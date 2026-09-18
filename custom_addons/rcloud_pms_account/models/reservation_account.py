# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class RcloudReservation(models.Model):
    _inherit = 'rcloud.reservation'

    def action_invoice_stay(self):
        """Invoice the stay: create the folio if missing, post its
        invoice, and move the reservation to 'invoiced'."""
        for res in self:
            if res.state not in ('checked_in', 'checked_out'):
                raise UserError(
                    _('Only checked-in or checked-out stays can be invoiced.'))
            if not res.folio_id:
                res.folio_id = self.env['rcloud.folio'].create({
                    'reservation_id': res.id,
                    'partner_id': res.guest_id.id,
                }).id
            invoice = res.folio_id.action_post_invoice()
            res.state = 'invoiced'
            res.message_post(body=_(
                'Stay invoiced: %s.') % invoice.name)
        return True
