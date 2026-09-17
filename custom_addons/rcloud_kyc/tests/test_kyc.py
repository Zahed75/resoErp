# -*- coding: utf-8 -*-
from datetime import timedelta

import odoo
from odoo import api
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKyc(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import os
        code = 'K%d' % (os.getpid() % 100000)
        cr = odoo.sql_db.db_connect(cls.env.cr.dbname).cursor()
        env = api.Environment(cr, cls.env.uid, {})
        cls.property = env['rcloud.property'].create({
            'name': 'KYC Resort %s' % code, 'code': code,
        })
        cls.room_type = env['rcloud.room.type'].create({
            'name': 'KYC Suite', 'property_id': cls.property.id,
            'default_rate': 9000.0,
        })
        cls.room = env['rcloud.room'].create({
            'name': 'K301', 'property_id': cls.property.id,
            'room_type_id': cls.room_type.id,
        })
        cls.guest = env['res.partner'].create({'name': 'KYC Guest'})
        ids = (cls.property.id, cls.room_type.id, cls.room.id, cls.guest.id)
        cr.commit()
        cr.close()
        # Re-browse through the class environment (see rcloud_pms tests).
        cls.property = cls.env['rcloud.property'].browse(ids[0])
        cls.room_type = cls.env['rcloud.room.type'].browse(ids[1])
        cls.room = cls.env['rcloud.room'].browse(ids[2])
        cls.guest = cls.env['res.partner'].browse(ids[3])
        cls.officer = cls.env['res.users'].create({
            'name': 'KYC Officer', 'login': 'kyc_officer_%d' % os.getpid(),
            'group_ids': [(4, cls.env.ref('rcloud_kyc.group_kyc_officer').id)],
        })
        cls.staff = cls.env['res.users'].create({
            'name': 'Front Desk', 'login': 'kyc_staff_%d' % os.getpid(),
            'group_ids': [(4, cls.env.ref(
                'rcloud_base.group_hotel_user').id)],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'KYC Manager', 'login': 'kyc_manager_%d' % os.getpid(),
            'group_ids': [(4, cls.env.ref(
                'rcloud_base.group_hotel_manager').id)],
        })
        cls.today = odoo.fields.Date.today()

    def _create_record(self, **kw):
        vals = {
            'partner_id': self.guest.id,
            'property_id': self.property.id,
            'doc_type': 'passport',
            'doc_number': 'P123456789',
        }
        vals.update(kw)
        return self.env['rcloud.kyc.record'].create(vals)

    # ------------------------------------------------------- state machine
    def test_state_machine(self):
        rec = self._create_record()
        self.assertEqual(rec.state, 'pending')

        rec.action_submit()
        self.assertEqual(rec.state, 'submitted')

        # Rejection requires a reason.
        with self.assertRaises(ValidationError):
            rec.with_user(self.officer).action_reject()

        rec.rejection_reason = 'Blurry scan'
        rec.with_user(self.officer).action_reject()
        self.assertEqual(rec.state, 'rejected')

        # A rejected record frees the partner/doc_type slot.
        rec2 = self._create_record()
        rec2.action_submit()
        rec2.with_user(self.officer).action_verify()
        self.assertEqual(rec2.state, 'verified')
        self.assertEqual(rec2.verified_by, self.officer)
        self.assertTrue(rec2.verified_on)

    def test_verify_requires_officer(self):
        rec = self._create_record()
        rec.action_submit()
        with self.assertRaises(UserError):
            rec.with_user(self.staff).action_verify()

    def test_single_open_record(self):
        self._create_record()
        with self.assertRaises(ValidationError):
            self._create_record()
        # Rejected records do not collide.
        rejected = self._create_record(doc_type='nid')
        rejected.action_submit()
        rejected.rejection_reason = 'Expired'
        rejected.with_user(self.officer).action_reject()
        self._create_record(doc_type='nid')

    # -------------------------------------------------------------- masking
    def test_number_masking(self):
        rec = self._create_record(doc_number='AB123456CD')
        self.assertEqual(rec.doc_number_display, 'AB****CD')
        rec_short = self._create_record(doc_type='nid', doc_number='123')
        self.assertEqual(rec_short.doc_number_display, '****')
        # The raw number is invisible to a plain officer without the field
        # groups? officer HAS the groups. Staff cannot even read the record.
        # Here we assert the field-level group on the raw number exists.
        field = self.env['rcloud.kyc.record']._fields['doc_number']
        self.assertTrue(field.groups)

    # ----------------------------------------------------------------- ACLs
    def test_staff_user_denied(self):
        rec = self._create_record()
        rec.action_submit()
        staff_env = self.env(user=self.staff)
        with self.assertRaises(AccessError):
            staff_env['rcloud.kyc.record'].browse(rec.id).read(['state'])

    def test_officer_can_read_write(self):
        rec = self._create_record()
        rec = rec.with_user(self.officer)
        self.assertEqual(rec.read(['state'])[0]['state'], 'pending')
        rec.write({'issuing_country': False})

    def test_manager_implies_officer(self):
        self.assertTrue(
            self.manager.has_group('rcloud_kyc.group_kyc_officer'))

    # --------------------------------------------------------- check-in guard
    def _reservation(self):
        arrival = self.today + timedelta(days=120)
        vals = {
            'property_id': self.property.id,
            'room_type_id': self.room_type.id,
            'guest_id': self.guest.id,
            'arrival': arrival,
            'departure': arrival + timedelta(days=2),
        }
        res = self.env['rcloud.reservation'].create(vals)
        self.env['rcloud.availability'].sudo().ensure_buckets(
            vals['property_id'], vals['room_type_id'],
            vals['arrival'], vals['departure'])
        res.action_confirm()
        return res

    def test_check_in_blocked_without_verified_kyc(self):
        self.property.kyc_required = True
        res = self._reservation()
        with self.assertRaises(UserError):
            res.action_check_in()

        rec = self._create_record()
        rec.action_submit()
        rec.with_user(self.officer).action_verify()
        res.action_check_in()
        self.assertEqual(res.state, 'checked_in')

    def test_check_in_allowed_when_kyc_not_required(self):
        self.property.kyc_required = False
        res = self._reservation()
        res.action_check_in()
        self.assertEqual(res.state, 'checked_in')

    # ----------------------------------------------------------------- GDPR
    def test_gdpr_erase(self):
        rec = self._create_record()
        attachment = self.env['ir.attachment'].create({
            'name': 'passport.pdf',
            'datas': 'aGVsbG8=',
            'res_model': 'rcloud.kyc.record',
            'res_id': rec.id,
        })
        rec.attachment_ids = [(4, attachment.id)]
        self.guest.phone = '+8801000000000'
        self.guest.action_gdpr_erase()
        self.assertEqual(self.guest.name, 'Erased')
        self.assertFalse(self.guest.phone)
        self.assertFalse(rec.attachment_ids)
        self.assertEqual(rec.doc_number, 'XXXX')
        self.assertEqual(rec.state, 'rejected')

    def test_gdpr_export(self):
        self._create_record()
        action = self.guest.action_gdpr_export()
        self.assertEqual(action['type'], 'ir.actions.act_url')
