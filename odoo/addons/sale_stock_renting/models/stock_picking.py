from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _should_ignore_backorders(self):
        return super()._should_ignore_backorders() and not any(move.sale_line_id.is_rental for move in self.move_ids)

    def _compute_location_id(self):
        super()._compute_location_id()

        if not self.move_ids.sale_line_id._are_rental_pickings_enabled():
            return

        for picking in self:
            if picking.picking_type_id.code == 'outgoing' \
                and any(move.sale_line_id.is_rental for move in picking.move_ids):
                picking.location_dest_id = picking.company_id.rental_loc_id
