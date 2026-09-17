# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOps(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.property = cls.env['rcloud.property'].create({
            'name': 'Ops Resort', 'code': 'OPS',
        })
        cls.room_type = cls.env['rcloud.room.type'].create({
            'name': 'Standard', 'property_id': cls.property.id,
            'default_rate': 5000.0,
        })
        cls.rooms = cls.env['rcloud.room'].create([
            {'name': '101', 'property_id': cls.property.id,
             'room_type_id': cls.room_type.id},
            {'name': '102', 'property_id': cls.property.id,
             'room_type_id': cls.room_type.id},
        ])
        cls.guest = cls.env['res.partner'].create({'name': 'Ops Guest'})
        cls.today = fields.Date.today()

    def _check_in(self, room, arrival, departure):
        res = self.env['rcloud.reservation'].create({
            'property_id': self.property.id,
            'room_type_id': self.room_type.id,
            'guest_id': self.guest.id,
            'arrival': arrival,
            'departure': departure,
        })
        self.env['rcloud.availability'].sudo().ensure_buckets(
            self.property.id, self.room_type.id, arrival, departure)
        res.action_confirm()
        res.action_check_in()
        self.assertEqual(res.room_id, room)
        return res

    def test_housekeeping_cron_and_task_lifecycle(self):
        yesterday = self.today - timedelta(days=1)
        stay_over = self._check_in(self.rooms[0], self.today,
                                   self.today + timedelta(days=2))
        departing = self._check_in(self.rooms[1], yesterday, self.today)

        tasks = self.env['rcloud.housekeeping.task'].sudo() \
            .cron_generate_tasks()
        by_type = {t.type: t for t in tasks}
        self.assertIn('stay_over', by_type)
        self.assertIn('departure_clean', by_type)
        self.assertEqual(by_type['stay_over'].room_id, self.rooms[0])
        self.assertEqual(by_type['departure_clean'].room_id, self.rooms[1])

        # Cron is idempotent for the same day.
        again = self.env['rcloud.housekeeping.task'].sudo() \
            .cron_generate_tasks()
        self.assertFalse(again)

        task = by_type['stay_over']
        task.action_start()
        self.assertEqual(task.state, 'in_progress')
        self.rooms[0].invalidate_recordset()
        task.action_done()
        self.assertEqual(task.state, 'done')
        self.assertEqual(self.rooms[0].housekeeping_state, 'clean')
        manager = self.env['res.users'].create({
            'name': 'Ops Manager', 'login': 'ops_manager',
            'group_ids': [(4, self.env.ref(
                'rcloud_base.group_hotel_manager').id)],
        })
        task.with_user(manager).action_verify()
        self.assertEqual(task.state, 'verified')

        task2 = by_type['departure_clean']
        with self.assertRaises(UserError):
            task2.action_done()  # not in progress yet

    def test_report_fault_opens_ticket_and_ooo_room(self):
        res = self._check_in(self.rooms[0], self.today,
                             self.today + timedelta(days=2))
        task = self.env['rcloud.housekeeping.task'].sudo().create({
            'property_id': self.property.id,
            'room_id': self.rooms[0].id,
            'date': self.today,
            'type': 'stay_over',
        })
        task.action_report_fault()
        ticket = self.env['rcloud.maintenance.ticket'].sudo().search([
            ('room_id', '=', self.rooms[0].id)])
        self.assertEqual(len(ticket), 1)
        self.assertEqual(ticket.state, 'new')
        self.assertTrue(self.rooms[0].is_ooo)

        ticket.action_start()
        self.assertEqual(ticket.state, 'in_progress')
        ticket.action_done()
        self.assertEqual(ticket.state, 'done')
        self.assertFalse(self.rooms[0].is_ooo)

    def test_night_audit_posts_room_charge_and_advances_date(self):
        res = self._check_in(self.rooms[0], self.today,
                             self.today + timedelta(days=2))
        folio = res.folio_id
        Audit = self.env['rcloud.night.audit.run'].sudo()
        Audit._set_business_date(self.today)
        run = Audit.create({'date': self.today})
        run.action_run()
        description = 'Room charge %s %s' % (self.rooms[0].name, self.today)
        lines = folio.line_ids.filtered(
            lambda l: l.description == description and
            l.date == self.today)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.qty, 1)
        self.assertEqual(lines.unit_price, 5000.0)  # reservation line rate
        self.assertEqual(lines.source, 'room')
        self.assertEqual(Audit._get_business_date(),
                         self.today + timedelta(days=1))

        # Running the audit again for the same date never duplicates.
        rerun = Audit.create({'date': self.today})
        rerun.action_run()
        lines = folio.line_ids.filtered(
            lambda l: l.description == description and
            l.date == self.today)
        self.assertEqual(len(lines), 1)

    def test_night_audit_skips_departing_guests(self):
        yesterday = self.today - timedelta(days=1)
        res = self._check_in(self.rooms[0], yesterday, self.today)
        folio = res.folio_id
        Audit = self.env['rcloud.night.audit.run'].sudo()
        run = Audit.create({'date': self.today})
        run.action_run()
        self.assertFalse(folio.line_ids)
