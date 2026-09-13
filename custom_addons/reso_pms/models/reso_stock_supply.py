# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoStockSupply(models.Model):
    _name = 'reso.stock.supply'
    _description = 'Reso Resort Inventory & Amenity Stock Item'
    _order = 'property_id, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Supply Item Name', required=True, tracking=True)
    property_id = fields.Many2one('reso.property', string='Property', required=True, index=True)
    category = fields.Selection([
        ('housekeeping', 'Housekeeping & Toiletries'),
        ('fb', 'Food & Beverage Ingredient'),
        ('minibar', 'Minibar Item'),
        ('linen', 'Linen & Bedding'),
        ('maintenance', 'Maintenance Spare Part'),
        ('office', 'Front Desk & Office'),
    ], string='Stock Category', default='housekeeping', required=True)

    quantity_on_hand = fields.Float(string='On Hand Quantity', default=0.0, tracking=True)
    min_quantity = fields.Float(string='Reorder Level (Min)', default=10.0)
    max_quantity = fields.Float(string='Target Quantity (Max)', default=100.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    unit_cost = fields.Monetary(string='Unit Cost', currency_field='currency_id')
    currency_id = fields.Many2one(related='property_id.currency_id', store=True, string='Currency')

    vendor_id = fields.Many2one('res.partner', string='Primary Vendor', domain="[('supplier_rank', '>', 0)]")
    reorder_needed = fields.Boolean(string='Reorder Needed', compute='_compute_reorder_needed', store=True)

    @api.depends('quantity_on_hand', 'min_quantity')
    def _compute_reorder_needed(self):
        for item in self:
            item.reorder_needed = item.quantity_on_hand <= item.min_quantity

    def action_create_reorder_po(self):
        """Creates an Odoo Purchase Order for auto-reordering when below min quantity."""
        for item in self:
            if not item.vendor_id:
                continue
            qty_to_order = max(item.max_quantity - item.quantity_on_hand, 1.0)
            po_vals = {
                'partner_id': item.vendor_id.id,
                'order_line': [(0, 0, {
                    'name': f"Auto-Reorder: {item.name} for {item.property_id.name}",
                    'product_qty': qty_to_order,
                    'price_unit': item.unit_cost,
                    'date_planned': fields.Datetime.now(),
                })]
            }
            if 'purchase.order' in self.env:
                self.env['purchase.order'].create(po_vals)
