# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RcloudRoom(models.Model):
    _name = 'rcloud.room'
    _description = 'Room / Villa'
    _order = 'property_id, name'
    _inherit = ['rcloud.property.mixin', 'mail.thread']

    name = fields.Char(string='Room No.', required=True)
    room_type_id = fields.Many2one(
        'rcloud.room.type', required=True, ondelete='restrict', index=True)
    floor = fields.Char()
    status = fields.Selection([
        ('vacant_clean', 'Vacant Clean'),
        ('vacant_dirty', 'Vacant Dirty'),
        ('occupied', 'Occupied'),
        ('out_of_order', 'Out of Order'),
    ], default='vacant_clean', required=True, tracking=True)
    is_ooo = fields.Boolean(string='Out of Order', default=False)
    housekeeping_state = fields.Selection([
        ('clean', 'Clean'),
        ('dirty', 'Dirty'),
        ('inspected', 'Inspected'),
    ], default='clean', required=True, tracking=True)

    _room_uniq = models.Constraint(
        'unique(property_id, name)',
        'A room with this number already exists on the property.')

    @api.constrains('property_id', 'room_type_id')
    def _check_type_property(self):
        for room in self:
            if room.room_type_id.property_id != room.property_id:
                raise ValidationError(
                    _('The room type must belong to the same property.'))

    @api.model_create_multi
    def create(self, vals_list):
        rooms = super().create(vals_list)
        rooms.mapped('room_type_id')._sync_availability_totals()
        return rooms

    def write(self, vals):
        res = super().write(vals)
        if 'is_ooo' in vals:
            self._apply_ooo_block()
        return res

    def _apply_ooo_block(self):
        """OOO rooms are immediately removed from availability."""
        Availability = self.env['rcloud.availability'].sudo()
        for room in self:
            rt = room.room_type_id
            Availability.ensure_buckets(
                rt.property_id.id, rt.id,
                fields.Date.today(), fields.Date.add(fields.Date.today(), days=365))
            buckets = Availability.search([('room_type_id', '=', rt.id)])
            if room.is_ooo:
                for b in buckets:
                    if not b.blocked:
                        b.block(1)
            else:
                for b in buckets:
                    if b.blocked:
                        b.unblock(1)

    def action_set_clean(self):
        self.write({'housekeeping_state': 'clean',
                    'status': 'vacant_clean'})

    def action_set_dirty(self):
        self.write({'housekeeping_state': 'dirty',
                    'status': 'vacant_dirty'})
