# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RcloudHousekeepingTask(models.Model):
    """Daily housekeeping work order per room."""

    _name = 'rcloud.housekeeping.task'
    _description = 'Housekeeping Task'
    _order = 'date, room_id, id'
    _inherit = ['rcloud.property.mixin', 'mail.thread']

    room_id = fields.Many2one(
        'rcloud.room', required=True, ondelete='cascade', index=True)
    date = fields.Date(
        required=True, default=fields.Date.today, index=True)
    type = fields.Selection([
        ('departure_clean', 'Departure Clean'),
        ('stay_over', 'Stay Over'),
        ('inspection', 'Inspection'),
    ], required=True)
    assignee_id = fields.Many2one('res.users', string='Assignee')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('verified', 'Verified'),
    ], default='pending', required=True, tracking=True)

    _task_uniq = models.Constraint(
        'unique(room_id, date, type)',
        'A task of this type already exists for the room on this date.')

    @api.constrains('property_id', 'room_id')
    def _check_room_property(self):
        for task in self:
            if task.room_id.property_id != task.property_id:
                raise ValidationError(
                    _('The room must belong to the same property.'))

    # ---------------------------------------------------------- generation
    @api.model
    def cron_generate_tasks(self):
        """05:00 cron: departure cleans for rooms departing today,
        stay overs for occupied rooms not departing."""
        today = fields.Date.context_today(self)
        reservations = self.env['rcloud.reservation'].sudo().search([
            ('state', '=', 'checked_in'),
            ('arrival', '<=', today),
            ('departure', '>=', today),
        ])
        Task = self.env['rcloud.housekeeping.task'].sudo()
        by_room_type = {}
        for res in reservations:
            if not res.room_id:
                continue
            task_type = ('departure_clean' if res.departure == today
                         else 'stay_over')
            by_room_type[(res.room_id.id, task_type)] = res
        vals_list = []
        for (room_id, task_type), res in by_room_type.items():
            if Task.search_count([
                    ('room_id', '=', room_id),
                    ('date', '=', today),
                    ('type', '=', task_type)]):
                continue
            vals_list.append({
                'property_id': res.property_id.id,
                'room_id': room_id,
                'date': today,
                'type': task_type,
            })
        return Task.create(vals_list)

    # ---------------------------------------------------------- lifecycle
    def action_start(self):
        for task in self:
            if task.state != 'pending':
                raise UserError(_('Only pending tasks can be started.'))
            task.state = 'in_progress'

    def action_done(self):
        for task in self:
            if task.state != 'in_progress':
                raise UserError(_('Only in-progress tasks can be done.'))
            task.state = 'done'
            if task.type != 'inspection' and \
                    task.room_id.housekeeping_state != 'clean':
                task.room_id.action_set_clean()

    def action_verify(self):
        if not self.env.user.has_group('rcloud_base.group_hotel_manager'):
            raise UserError(_('Only hotel managers can verify tasks.'))
        for task in self:
            if task.state != 'done':
                raise UserError(_('Only done tasks can be verified.'))
            task.state = 'verified'

    def action_report_fault(self):
        """Flag the room out of order and open a maintenance ticket."""
        self.ensure_one()
        ticket = self.env['rcloud.maintenance.ticket'].sudo().create({
            'property_id': self.property_id.id,
            'room_id': self.room_id.id,
            'title': _('Fault in room %s') % self.room_id.name,
            'priority': 'high',
        })
        self.room_id.is_ooo = True
        self.message_post(body=_(
            'Fault reported, maintenance ticket %s opened. Room set '
            'out of order.') % ticket.name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rcloud.maintenance.ticket',
            'res_id': ticket.id,
            'view_mode': 'form',
            'target': 'current',
        }


class RcloudMaintenanceTicket(models.Model):
    _name = 'rcloud.maintenance.ticket'
    _description = 'Maintenance Ticket'
    _order = 'id desc'
    _inherit = ['rcloud.property.mixin', 'mail.thread']

    name = fields.Char(
        readonly=True, copy=False, default='New', required=True)
    room_id = fields.Many2one(
        'rcloud.room', string='Room', ondelete='set null', index=True)
    title = fields.Char(required=True)
    description = fields.Text()
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], default='medium', required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], default='new', required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rcloud.maintenance.ticket') or 'New'
        return super().create(vals_list)

    @api.constrains('property_id', 'room_id')
    def _check_room_property(self):
        for ticket in self:
            if ticket.room_id and \
                    ticket.room_id.property_id != ticket.property_id:
                raise ValidationError(
                    _('The room must belong to the same property.'))

    def action_start(self):
        for ticket in self:
            if ticket.state != 'new':
                raise UserError(_('Only new tickets can be started.'))
            ticket.state = 'in_progress'

    def action_done(self):
        for ticket in self:
            if ticket.state != 'in_progress':
                raise UserError(_('Only in-progress tickets can be done.'))
            ticket.state = 'done'
            if ticket.room_id and ticket.room_id.is_ooo:
                ticket.room_id.is_ooo = False
