# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResoMaintenanceTicket(models.Model):
    _name = 'reso.maintenance.ticket'
    _description = 'Reso Maintenance Ticket'
    _order = 'priority desc, request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Ticket Ref', required=True, readonly=True,
                       copy=False, default='New')
    title = fields.Char(string='Subject / Problem', required=True)
    property_id = fields.Many2one(
        'reso.property', string='Property', required=True,
        ondelete='restrict', index=True)
    room_id = fields.Many2one(
        'reso.room', string='Room / Area',
        domain="[('property_id', '=', property_id)]")
    assigned_user_id = fields.Many2one('res.users', string='Assigned Technician', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='new', tracking=True)
    request_date = fields.Datetime(string='Requested On', default=fields.Datetime.now, required=True)
    resolution_date = fields.Datetime(string='Resolved On')
    description = fields.Text(string='Description / Resolution Notes')
    company_id = fields.Many2one(
        related='property_id.company_id', store=True, index=True,
        string='Company')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'reso.maintenance.ticket') or 'MT/00001'
        tickets = super().create(vals_list)
        for ticket in tickets:
            if ticket.room_id and ticket.priority in ('2', '3') and ticket.state in ('new', 'in_progress'):
                ticket.room_id.status = 'maintenance'
        return tickets

    def action_start(self):
        for ticket in self:
            ticket.state = 'in_progress'
            if ticket.room_id:
                ticket.room_id.status = 'maintenance'

    def action_resolve(self):
        for ticket in self:
            ticket.write({
                'state': 'resolved',
                'resolution_date': fields.Datetime.now(),
            })
            if ticket.room_id:
                # Check if there are remaining open maintenance tickets for this room
                other_open = self.search([
                    ('id', '!=', ticket.id),
                    ('room_id', '=', ticket.room_id.id),
                    ('state', 'in', ('new', 'in_progress')),
                ])
                if not other_open:
                    ticket.room_id.status = 'available'

    def action_cancel(self):
        for ticket in self:
            ticket.state = 'cancelled'
            if ticket.room_id:
                other_open = self.search([
                    ('id', '!=', ticket.id),
                    ('room_id', '=', ticket.room_id.id),
                    ('state', 'in', ('new', 'in_progress')),
                ])
                if not other_open and ticket.room_id.status == 'maintenance':
                    ticket.room_id.status = 'available'
