# -*- coding: utf-8 -*-
import random
from datetime import timedelta

from odoo import api, fields, models


class ResoDemoLoader(models.AbstractModel):
    """Generates bulk demo records (guests, bookings, folio charges) so the
    dashboard, analytics and reports can be explored with realistic volume.
    Invoked once from demo/demo_data.xml via a <function> node."""

    _name = 'reso.demo.loader'
    _description = 'Reso Bulk Demo Data Generator'

    GUEST_NAMES = [
        'Ayesha Khan', 'Farhan Hossain', 'Maria Gonzalez', 'James OConnor',
        'Priya Sharma', 'Mohammad Rakib', 'Emma Wilson', 'Tanaka Yuki',
        'Liam Murphy', 'Fatima Noor', 'Sofia Rossi', 'Arif Chowdhury',
        'Hannah Schmidt', 'Rashid Khan', 'Lucas Silva', 'Nabila Akter',
        'Oliver Chen', 'Sumaiya Islam', 'Noah Brown', 'Jannat Ara',
        'Ethan Wright', 'Mahmud Hasan', 'Chloe Davis', 'Shirin Sultana',
    ]

    FOLIO_ITEMS = [
        ('restaurant', 'Dinner — Seaside Grill', 1200, 3200),
        ('restaurant', 'Breakfast buffet (2 pax)', 500, 900),
        ('bar', 'Evening cocktails', 400, 1600),
        ('spa', 'Aromatherapy massage (60 min)', 2200, 3500),
        ('spa', 'Facial & sauna session', 1500, 2800),
        ('excursion', 'Guided island snorkelling', 1200, 2600),
        ('excursion', 'Sunset boat cruise', 1800, 4000),
        ('laundry', 'Laundry & pressing service', 300, 800),
        ('minibar', 'Minibar restock', 450, 1200),
    ]

    @api.model
    def load_bulk_demo_data(self):
        # Idempotency marker: never generate the bulk set twice, even if the
        # demo file is re-processed on a later module upgrade.
        if self.env['ir.model.data'].sudo().search_count([
                ('module', '=', 'reso_pms'),
                ('name', '=', 'demo_bulk_data_loaded')]):
            return True
        self.env['ir.model.data'].sudo().create({
            'module': 'reso_pms',
            'name': 'demo_bulk_data_loaded',
            'model': 'ir.model.data',
            'res_id': 0,
            'noupdate': True,
        })

        Booking = self.env['reso.booking']
        today = fields.Date.today()
        properties = self.env['reso.property'].search([])
        if not properties:
            return True

        # ---- Guests -------------------------------------------------------
        partners = self.env['res.partner']
        for i, name in enumerate(self.GUEST_NAMES):
            partners |= self.env['res.partner'].create({
                'name': name,
                'phone': '+88017%08d' % (10000000 + i * 137),
                'email': '%s@example.com' % name.lower().replace(' ', '.'),
            })

        # ---- Bookings: past 12 months (stays) + next 30 days (upcoming) ---
        bookings = self.env['reso.booking']
        for i in range(120):
            prop = properties[i % len(properties)]
            room_types = self.env['reso.room.type'].search([
                ('property_id', '=', prop.id)])
            if not room_types:
                continue
            room_type = room_types[i % len(room_types)]
            partner = partners[i % len(partners)]
            nights = random.randint(1, 6)
            adults = random.randint(1, min(room_type.max_guests or 2, 4))

            if i < 90:
                # Historical stays spread over the past year
                checkin = today - timedelta(days=random.randint(7, 360))
                state = 'checked_out' if random.random() < 0.8 else 'invoiced'
                source = random.choice(
                    ['website', 'ota', 'direct', 'phone', 'agent', 'walk_in'])
            elif i < 105:
                # In-house right now (drives arrivals/in-house KPIs)
                checkin = today - timedelta(days=random.randint(0, 2))
                state = 'checked_in'
                source = random.choice(['direct', 'website', 'walk_in'])
            else:
                # Upcoming reservations
                checkin = today + timedelta(days=random.randint(1, 30))
                state = random.choice(['confirmed', 'confirmed', 'hold'])
                source = random.choice(['website', 'phone', 'ota', 'agent'])

            bookings |= Booking.create({
                'property_id': prop.id,
                'partner_id': partner.id,
                'room_type_id': room_type.id,
                'checkin_date': checkin,
                'checkout_date': checkin + timedelta(days=nights),
                'adults': adults,
                'children': random.randint(0, 2) if adults < 3 else 0,
                'source': source,
                'state': state,
            })

        # ---- Folio outlet charges on historical stays ----------------------
        folio_lines = self.env['reso.booking.folio.line']
        for booking in bookings.filtered(lambda b: b.state in ('checked_out', 'invoiced')):
            for _outlet, label, low, high in random.sample(
                    self.FOLIO_ITEMS, k=random.randint(0, 3)):
                folio_lines |= folio_lines.create({
                    'booking_id': booking.id,
                    'name': label,
                    'outlet_type': _outlet,
                    'quantity': random.randint(1, 2),
                    'price_unit': float(random.randint(low, high)),
                    'date': '%s 20:30:00' % booking.checkin_date,
                })

        # ---- A sprinkle of guest messages ---------------------------------
        WhatsApp = self.env['reso.whatsapp.message']
        for partner in partners[:10]:
            WhatsApp.create({
                'partner_id': partner.id,
                'phone': partner.phone,
                'message_type': 'inbound',
                'body': random.choice([
                    'What time is check-in?',
                    'Can we get a late check-out tomorrow?',
                    'Is breakfast included in the rate?',
                    'Please arrange an airport pickup.',
                ]),
                'state': 'delivered',
            })

        return True
