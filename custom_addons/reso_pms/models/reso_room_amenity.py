# -*- coding: utf-8 -*-
from odoo import fields, models


class ResoRoomAmenity(models.Model):
    _name = 'reso.room.amenity'
    _description = 'Room Amenity'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
