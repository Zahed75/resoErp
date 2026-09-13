from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_retrieval_product_search_plan(self):
        # EXTENDS product.product
        search_plan = super()._get_retrieval_product_search_plan()

        # retrieve product from name can be disabled in the settings, if so, we remove it from the search plan
        disable_search_by_name = not self.env.company.predict_bill_product
        return [
            method for method in search_plan
            if not (disable_search_by_name and method[1] == self._import_retrieve_product_from_name)
        ]
