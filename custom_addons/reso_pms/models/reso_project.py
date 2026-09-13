# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResoCapexProject(models.Model):
    _name = 'reso.capex.project'
    _description = 'Reso Resort CAPEX & Renovation Project'
    _order = 'start_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True, tracking=True)
    property_id = fields.Many2one('reso.property', string='Property', required=True, index=True)
    project_type = fields.Selection([
        ('renovation', 'Villa / Room Renovation'),
        ('expansion', 'Property Expansion / New Units'),
        ('infrastructure', 'Infrastructure / Utility Overhaul'),
        ('amenity', 'Amenity & Pool Upgrade'),
        ('capex', 'General CAPEX Works'),
    ], string='Project Type', default='renovation', required=True)

    budget = fields.Monetary(string='Estimated Budget', required=True, currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Expenditure', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(related='property_id.currency_id', store=True, string='Currency')

    start_date = fields.Date(string='Start Date', default=fields.Date.today)
    target_end_date = fields.Date(string='Target Completion')
    actual_end_date = fields.Date(string='Actual Completion')

    manager_id = fields.Many2one('res.users', string='Project Manager')
    state = fields.Selection([
        ('draft', 'Planning / Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    progress_percent = fields.Float(string='Completion (%)', default=0.0)
    description = fields.Text(string='Project Scope & Specifications')

    def action_start(self):
        for proj in self:
            proj.state = 'in_progress'

    def action_complete(self):
        for proj in self:
            proj.write({
                'state': 'completed',
                'actual_end_date': fields.Date.today(),
                'progress_percent': 100.0,
            })
