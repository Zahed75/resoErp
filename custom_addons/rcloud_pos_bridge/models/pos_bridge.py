# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class RcloudFolio(models.Model):
    _inherit = 'rcloud.folio'

    pos_charge_ids = fields.One2many(
        'pos.order', 'rcloud_folio_id', string='POS Charges', readonly=True)

    def add_pos_charge(self, lines, reference=None):
        """Post POS charge lines onto this folio.

        :param lines: iterable of dicts {description, qty, unit_price,
            product_id?, source?} — or a pos.order recordset whose lines
            are read automatically.
        :returns: created rcloud.folio.line recordset
        """
        self.ensure_one()
        if self.state != 'open':
            raise UserError(_('Cannot post POS charges to a closed folio.'))
        if hasattr(lines, '_name') and lines._name == 'pos.order':
            order = lines
            if order.rcloud_folio_id and order.rcloud_folio_id != self:
                raise UserError(_('This order is already charged to %s.') %
                                order.rcloud_folio_id.name)
            values = [{
                'description': line.product_id.display_name or 'POS item',
                'product_id': line.product_id.id,
                'qty': line.qty,
                'unit_price': line.price_unit,
                'source': 'pos',
            } for line in order.lines]
            order.rcloud_folio_id = self.id
        else:
            values = [dict(
                description=v.get('description', 'POS item'),
                product_id=v.get('product_id'),
                qty=v.get('qty', 1.0),
                unit_price=v.get('unit_price', 0.0),
                source=v.get('source', 'pos'),
            ) for v in lines]
        if not values:
            raise UserError(_('Nothing to charge.'))
        created = self.env['rcloud.folio.line'].create([
            dict(v, folio_id=self.id, date=fields.Date.today())
            for v in values
        ])
        self.message_post(body=_('POS charge posted: %s (%d items)') % (
            reference or self.name, len(created)))
        return created


class PosOrder(models.Model):
    _inherit = 'pos.order'

    rcloud_folio_id = fields.Many2one(
        'rcloud.folio', string='Guest Folio', readonly=True, copy=False,
        help='Folio this order is charged to; settled at checkout.')

    def action_charge_to_room(self):
        self.ensure_one()
        if self.rcloud_folio_id:
            raise UserError(_('Already charged to %s.') %
                            self.rcloud_folio_id.name)
        folio = self.env['rcloud.folio'].sudo().search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'open'),
        ], order='id desc', limit=1)
        if not folio:
            raise UserError(_('No open folio for %s.') %
                            (self.partner_id.name or _('this customer')))
        folio.add_pos_charge(self)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rcloud.folio',
            'res_id': folio.id,
            'views': [[False, 'form']],
            'target': 'current',
        }
