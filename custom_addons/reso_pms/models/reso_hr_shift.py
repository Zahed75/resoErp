# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoHrShift(models.Model):
    _name = 'reso.hr.shift'
    _description = 'Reso Resort Employee Shift & Biometric Attendance Log'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Shift Ref', required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True)
    property_id = fields.Many2one('reso.property', string='Assigned Property', required=True)
    department = fields.Selection([
        ('front_desk', 'Front Desk & Concierge'),
        ('housekeeping', 'Housekeeping'),
        ('fb', 'Food & Beverage / Kitchen'),
        ('maintenance', 'Maintenance & Engineering'),
        ('security', 'Security & Grounds'),
        ('management', 'Administration & Management'),
    ], string='Department', default='housekeeping', required=True)

    date = fields.Date(string='Shift Date', default=fields.Date.today, required=True)
    shift_type = fields.Selection([
        ('morning', 'Morning (06:00 - 14:00)'),
        ('evening', 'Evening (14:00 - 22:00)'),
        ('night', 'Night (22:00 - 06:00)'),
        ('full_day', 'Full Day (09:00 - 18:00)'),
    ], string='Shift Type', default='morning', required=True)

    check_in_time = fields.Datetime(string='Biometric Check-In')
    check_out_time = fields.Datetime(string='Biometric Check-Out')
    biometric_device_id = fields.Char(string='Device Terminal Ref')

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('present', 'Present / Active'),
        ('completed', 'Completed'),
        ('absent', 'Absent / Late'),
    ], string='Shift Status', default='scheduled', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('reso.hr.shift') or 'SFT/00001'
        return super().create(vals_list)

    def action_clock_in(self):
        for shift in self:
            shift.write({
                'check_in_time': fields.Datetime.now(),
                'state': 'present',
            })

    def action_clock_out(self):
        for shift in self:
            shift.write({
                'check_out_time': fields.Datetime.now(),
                'state': 'completed',
            })
