# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestResoBooking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.property = cls.env['reso.property'].create({
            'name': 'Test Resort',
            'code': 'TST',
        })
        cls.room_type = cls.env['reso.room.type'].create({
            'name': 'Test King',
            'property_id': cls.property.id,
            'max_guests': 2,
        })
        cls.room = cls.env['reso.room'].create({
            'name': '301',
            'property_id': cls.property.id,
            'room_type_id': cls.room_type.id,
        })
        cls.rate_plan = cls.env['reso.rate.plan'].create({
            'name': 'Test Rate',
            'property_id': cls.property.id,
            'room_type_id': cls.room_type.id,
            'base_price': 1000.0,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Test Guest'})
        cls.other_property = cls.env['reso.property'].create({
            'name': 'Other Resort',
            'code': 'OTH',
        })

    def _create_booking(self, **extra):
        values = {
            'property_id': self.property.id,
            'partner_id': self.partner.id,
            'room_type_id': self.room_type.id,
            'checkin_date': '2026-10-01',
            'checkout_date': '2026-10-04',
        }
        values.update(extra)
        return self.env['reso.booking'].create(values)

    def test_01_booking_sequence(self):
        booking = self._create_booking()
        self.assertTrue(booking.name.startswith('BK/'),
                        "Booking should get a BK/ sequence number")

    def test_02_state_transitions(self):
        booking = self._create_booking()
        self.assertEqual(booking.state, 'hold')
        booking.action_confirm()
        self.assertEqual(booking.state, 'confirmed')
        booking.action_check_in()
        self.assertEqual(booking.state, 'checked_in')
        booking.action_check_out()
        self.assertEqual(booking.state, 'checked_out')

    def test_03_cancel_from_hold(self):
        booking = self._create_booking()
        booking.action_cancel()
        self.assertEqual(booking.state, 'cancelled')

    def test_04_invalid_dates(self):
        with self.assertRaises(ValidationError):
            self._create_booking(checkout_date='2026-10-01')

    def test_05_amount_total(self):
        booking = self._create_booking()
        nights = (booking.checkout_date - booking.checkin_date).days
        self.assertEqual(booking.amount_total, nights * 1000.0)

    def test_06_overlapping_seasons(self):
        self.rate_plan.season_line_ids = [
            (0, 0, {'date_from': '2026-12-01', 'date_to': '2026-12-15',
                    'price': 1500.0}),
        ]
        with self.assertRaises(ValidationError):
            self.rate_plan.season_line_ids = [
                (0, 0, {'date_from': '2026-12-10', 'date_to': '2026-12-20',
                        'price': 1800.0}),
            ]

    def test_07_room_type_property_mismatch(self):
        other_type = self.env['reso.room.type'].create({
            'name': 'Other King',
            'property_id': self.other_property.id,
        })
        with self.assertRaises(ValidationError):
            self.env['reso.room'].create({
                'name': '999',
                'property_id': self.property.id,
                'room_type_id': other_type.id,
            })

    def test_08_overlapping_booking_conflict(self):
        b1 = self._create_booking(room_id=self.room.id)
        b1.action_confirm()
        with self.assertRaises(ValidationError):
            b2 = self._create_booking(room_id=self.room.id)

    def test_09_housekeeping_and_checkin_checkout_status(self):
        booking = self._create_booking(room_id=self.room.id)
        booking.action_confirm()
        booking.action_check_in()
        self.assertEqual(self.room.status, 'occupied')
        booking.action_check_out()
        self.assertEqual(self.room.status, 'cleaning')
        self.assertEqual(self.room.housekeeping_status, 'dirty')
        self.room.action_mark_clean()
        self.assertEqual(self.room.housekeeping_status, 'clean')
        self.assertEqual(self.room.status, 'available')

    def test_10_maintenance_ticket_lifecycle(self):
        ticket = self.env['reso.maintenance.ticket'].create({
            'title': 'AC Repair',
            'property_id': self.property.id,
            'room_id': self.room.id,
            'priority': '3',
        })
        self.assertEqual(self.room.status, 'maintenance')
        ticket.action_resolve()
        self.assertEqual(ticket.state, 'resolved')
        self.assertEqual(self.room.status, 'available')

    def test_11_crm_lead_to_booking_conversion(self):
        lead = self.env['crm.lead'].create({
            'name': 'Inquiry for Ocean Villa',
            'partner_id': self.partner.id,
            'property_id': self.property.id,
            'room_type_id': self.room_type.id,
            'lead_type': 'guest',
            'preferred_checkin': '2026-11-01',
            'preferred_checkout': '2026-11-04',
        })
        action = lead.action_convert_to_booking()
        booking = self.env['reso.booking'].browse(action['res_id'])
        self.assertEqual(booking.partner_id, self.partner)
        self.assertEqual(booking.property_id, self.property)
        self.assertEqual(booking.room_type_id, self.room_type)

    def test_12_whatsapp_chatbot_rule_matching(self):
        rule = self.env['reso.whatsapp.chatbot.rule'].create({
            'name': 'Check-in Policy',
            'trigger_keywords': 'checkin, check-in, timing',
            'response_template': 'Standard check-in time is 2:00 PM.',
            'category': 'general',
        })
        self.assertTrue(rule.match_message('What is the check-in time?'))
        self.assertFalse(rule.match_message('How much for breakfast?'))

    def test_13_document_verification(self):
        doc = self.env['reso.document'].create({
            'name': 'Guest Passport ID',
            'document_type': 'passport',
            'partner_id': self.partner.id,
            'property_id': self.property.id,
        })
        self.assertFalse(doc.is_verified)
        doc.action_verify()
        self.assertTrue(doc.is_verified)
        doc.action_unverify()
        self.assertFalse(doc.is_verified)

    def test_14_stock_reorder_level(self):
        supply = self.env['reso.stock.supply'].create({
            'name': 'Shampoo Bottles 50ml',
            'property_id': self.property.id,
            'category': 'housekeeping',
            'quantity_on_hand': 5.0,
            'min_quantity': 20.0,
            'max_quantity': 100.0,
        })
        self.assertTrue(supply.reorder_needed)

    def test_15_hr_shift_clock(self):
        emp = self.env['hr.employee'].create({
            'name': 'Test Resort Staff',
        })
        shift = self.env['reso.hr.shift'].create({
            'employee_id': emp.id,
            'property_id': self.property.id,
            'department': 'housekeeping',
            'shift_type': 'morning',
        })
        self.assertEqual(shift.state, 'scheduled')
        shift.action_clock_in()
        self.assertEqual(shift.state, 'present')
        shift.action_clock_out()
        self.assertEqual(shift.state, 'completed')

    def test_16_capex_project_lifecycle(self):
        proj = self.env['reso.capex.project'].create({
            'name': 'Villa Pool Renovation',
            'property_id': self.property.id,
            'project_type': 'renovation',
            'budget': 500000.0,
        })
        self.assertEqual(proj.state, 'draft')
        proj.action_start()
        self.assertEqual(proj.state, 'in_progress')
        proj.action_complete()
        self.assertEqual(proj.state, 'completed')
        self.assertEqual(proj.progress_percent, 100.0)

    def test_17_dashboard_stats(self):
        Booking = self.env['reso.booking']
        stats = Booking.get_dashboard_stats()
        self.assertGreaterEqual(stats['rooms_total'], 1)
        self.assertIn('occupancy_rate', stats)
        self.assertIn('adr', stats)
        self.assertIn('revpar', stats)

        # A stay checked out within the 30-day window drives revenue metrics.
        booking = self._create_booking(
            checkin_date='2026-09-01',
            checkout_date='2026-09-03',
            state='checked_out',
        )
        stats = Booking.get_dashboard_stats(self.property.id)
        self.assertEqual(stats['rooms_total'], 1)
        # 2 nights x 1000 base price
        self.assertEqual(stats['room_nights_30d'], 2)
        self.assertEqual(stats['revenue_30d'], booking.amount_total)
        self.assertEqual(stats['adr'], booking.amount_total / 2)
        self.assertEqual(stats['revpar'], round(booking.amount_total / 30.0, 0))
        # reso_ownership is installed in this test DB, so ownership figures
        # must be reported (not None).
        self.assertTrue(stats['ownership_installed'])
        self.assertIsNotNone(stats['fractional_owners'])

    def test_18_maintenance_room_not_auto_assigned(self):
        """Rooms under maintenance or out of order must not be auto-assigned."""
        self.room.status = 'maintenance'
        spare = self.env['reso.room'].create({
            'name': '302',
            'property_id': self.property.id,
            'room_type_id': self.room_type.id,
        })
        booking = self._create_booking()
        booking.action_assign_room()
        self.assertEqual(booking.room_id, spare,
                         "Auto-assign must skip the maintenance room")
        spare.status = 'out_of_order'
        booking2 = self._create_booking(
            checkin_date='2026-10-10',
            checkout_date='2026-10-12',
        )
        booking2.action_assign_room()
        self.assertFalse(booking2.room_id,
                         "Auto-assign must not pick out-of-order rooms")

    def test_19_payment_state_guards(self):
        """Model-level behaviour mirrored by /api/v1/payment/process guards:
        a cancelled booking must never be confirmable, and confirming an
        already-confirmed booking must be a safe no-op (idempotency)."""
        booking = self._create_booking()
        booking.action_cancel()
        booking.action_confirm()
        self.assertEqual(booking.state, 'cancelled',
                         "Cancelled booking must not be confirmable")

        booking2 = self._create_booking(checkin_date='2026-10-20',
                                        checkout_date='2026-10-22')
        booking2.action_confirm()
        booking2.action_confirm()
        self.assertEqual(booking2.state, 'confirmed',
                         "Re-confirming must stay idempotent")
