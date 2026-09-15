# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class ResoWebsiteFrontend(http.Controller):
    """Public-facing hotel/resort booking website — liquid glass modern design."""

    def _properties(self):
        return request.env['reso.property'].sudo().search([('active', '=', True)])

    @http.route('/resort', type='http', auth='public', website=False, sitemap=True)
    def resort_home(self, **kwargs):
        properties = self._properties()
        room_types = request.env['reso.room.type'].sudo().search([], limit=6)
        return request.render('reso_pms.website_home', {
            'properties': properties,
            'room_types': room_types,
        })

    @http.route('/resort/rooms', type='http', auth='public', website=False, sitemap=True)
    def resort_rooms(self, **kwargs):
        properties = self._properties()
        room_types = request.env['reso.room.type'].sudo().search([])
        rate_plans = request.env['reso.rate.plan'].sudo().search([])
        rate_by_room_type = {rp.room_type_id.id: rp for rp in rate_plans}
        rooms_data = []
        for rt in room_types:
            rp = rate_by_room_type.get(rt.id)
            rooms_data.append({
                'id': rt.id,
                'name': rt.name,
                'property_name': rt.property_id.name,
                'property_id': rt.property_id.id,
                'max_guests': rt.max_guests,
                'bed_type': rt.bed_type,
                'price': rp.base_price if rp else 0.0,
                'currency': rp.currency_id.symbol if rp and rp.currency_id else request.env.company.currency_id.symbol,
                'amenities': [a.name for a in rt.amenity_ids][:4],
            })
        return request.render('reso_pms.website_rooms', {
            'properties': properties,
            'rooms_data': rooms_data,
        })

    @http.route('/resort/book', type='http', auth='public', website=False, sitemap=True)
    def resort_book(self, **kwargs):
        properties = self._properties()
        return request.render('reso_pms.website_book', {
            'properties': properties,
        })

    @http.route('/resort/contact', type='http', auth='public', website=False, sitemap=True)
    def resort_contact(self, **kwargs):
        properties = self._properties()
        return request.render('reso_pms.website_contact', {
            'properties': properties,
        })

    @http.route('/resort/booking/confirmation', type='http', auth='public', website=False)
    def resort_booking_confirmation(self, ref=None, **kwargs):
        booking = None
        if ref:
            booking = request.env['reso.booking'].sudo().search([('name', '=', ref)], limit=1)
        return request.render('reso_pms.website_confirmation', {
            'booking': booking,
        })
