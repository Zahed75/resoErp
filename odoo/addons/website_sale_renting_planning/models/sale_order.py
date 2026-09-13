# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _available_dates_for_renting(self):
        return (
            super()._available_dates_for_renting()
            and all(
                len(line._get_planning_resources_available()) >= int(line.product_uom_qty)
                for line in self.order_line
                if line._is_planning_rental_service()
                and line.product_id.planning_role_id.sync_shift_rental
            )
        )

    def _verify_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        new_qty, warning = super()._verify_updated_quantity(
            order_line, product_id, new_qty, uom_id, **kwargs
        )
        product = self.env['product.product'].browse(product_id)
        renting_availabilities = product._renting_product_availabilities(
            kwargs.get('start_date', order_line.start_date),
            kwargs.get('end_date', order_line.return_date)
        )
        max_qty = min(
            (a['quantity_available'] for a in renting_availabilities),
            default=float('inf')
        )
        if new_qty > max_qty:
            self.shop_warning = self._build_warning_renting(product)
            return max_qty, self.shop_warning

        return new_qty, warning

    def _is_valid_renting_dates(self):
        self.ensure_one()
        if not super()._is_valid_renting_dates():
            return False
        for order_line in self.order_line:
            renting_availabilities = order_line.product_id._renting_product_availabilities(
                self.rental_start_date or order_line.start_date,
                self.rental_return_date or order_line.return_date
            )
            max_qty = min(
                (a['quantity_available'] for a in renting_availabilities),
                default=float('inf')  # No renting availabilities means no constraint
            )
            if order_line.product_qty > max_qty:
                return False
        return True
