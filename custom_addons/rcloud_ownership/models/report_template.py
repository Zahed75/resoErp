# -*- coding: utf-8 -*-
import csv
import io

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import pycompat


class RcloudOwnerReportTemplate(models.Model):
    """Saved owner-statement report definition, runnable from the backend
    or the owner portal (PDF) and downloadable as CSV."""

    _name = 'rcloud.owner.report.template'
    _description = 'Owner Report Template'
    _order = 'name'

    name = fields.Char(required=True)
    owner_id = fields.Many2one(
        'rcloud.owner', string='Owner',
        help='Leave empty to report on all owners.')
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    property_ids = fields.Many2many(
        'rcloud.property', string='Properties')
    grouping = fields.Selection([
        ('none', 'No Grouping'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
        ('property', 'Property'),
    ], default='none', required=True)
    metrics = fields.Selection([
        ('gross', 'Gross Allocated'),
        ('deductions', 'Deductions'),
        ('net', 'Net Payable'),
    ], default='net', required=True,
        help='Metric highlighted in the report; all three are shown.')
    email_monthly = fields.Boolean(
        string='Email Monthly',
        help='Sent by the monthly scheduled action with the PDF attached.')

    def _forced_owner(self):
        """Portal users may only ever see their own figures."""
        user = self.env.user
        if user.has_group('base.group_portal') and \
                not user.has_group('base.group_user'):
            owner = self.env['rcloud.owner'].sudo().search(
                [('portal_user_id', '=', user.id)], limit=1)
            if not owner:
                raise UserError(
                    _('No owner record is linked to your portal user.'))
            return owner
        return None

    def _line_domain(self):
        self.ensure_one()
        domain = [
            ('run_id.period_end', '>=', self.date_from),
            ('run_id.period_start', '<=', self.date_to),
            ('run_id.state', 'in', ('posted', 'paid')),
        ]
        forced = self._forced_owner()
        if forced:
            domain.append(('owner_id', '=', forced.id))
        elif self.owner_id:
            domain.append(('owner_id', '=', self.owner_id.id))
        properties = self.sudo().property_ids
        if properties:
            domain.append(('property_id', 'in', properties.ids))
        return domain

    def _group_key(self, line):
        self.ensure_one()
        if self.grouping == 'none':
            return _('All')
        start = line.run_id.period_start
        if self.grouping == 'month':
            return '%04d-%02d' % (start.year, start.month)
        if self.grouping == 'quarter':
            return '%04d Q%d' % (start.year, ((start.month - 1) // 3) + 1)
        if self.grouping == 'year':
            return '%04d' % start.year
        return line.run_id.property_id.name

    def get_report_rows(self):
        """Aggregated {group: {gross, deductions, net, line_count}}."""
        self.ensure_one()
        lines = self.env['rcloud.distribution.line'].sudo().search(
            self._line_domain())
        rows = {}
        for line in lines:
            key = self._group_key(line)
            row = rows.setdefault(key, {
                'group': key, 'gross': 0.0, 'deductions': 0.0,
                'net': 0.0, 'line_count': 0})
            row['gross'] += line.gross_allocated
            row['deductions'] += line.deductions
            row['net'] += line.net_payable
            row['line_count'] += 1
        for row in rows.values():
            row['gross'] = round(row['gross'], 2)
            row['deductions'] = round(row['deductions'], 2)
            row['net'] = round(row['net'], 2)
        return [rows[k] for k in sorted(rows)]

    def action_run(self):
        self.ensure_one()
        return self.env.ref(
            'rcloud_ownership.action_report_owner_custom'
        ).report_action(self.ids)

    def action_email(self):
        """Render the PDF and send it by email (owner, or every owner with
        portal access when the template is not owner-specific)."""
        self.ensure_one()
        report = self.env.ref(
            'rcloud_ownership.action_report_owner_custom')
        owners = self.owner_id or self.env['rcloud.owner'].sudo().search(
            [('portal_user_id', '!=', False)])
        if not owners:
            raise UserError(_('There is no owner to email this report to.'))
        pdf, _mime = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report.report_name, self.ids)
        attachment = self.env['ir.attachment'].sudo().create({
            'name': '%s.pdf' % self.name,
            'type': 'binary',
            'datas': pdf,
            'res_model': self._name,
            'res_id': self.id,
        })
        mail_values = []
        for owner in owners:
            mail_values.append({
                'subject': _('%s — Owner Statement') % self.name,
                'email_to': owner.partner_id.email,
                'body_html': _(
                    '<p>Dear %s,</p><p>Please find your owner statement '
                    '"%s" attached.</p>') % (
                    owner.partner_id.name or '', self.name),
                'attachment_ids': [(4, attachment.id)],
            })
        self.env['mail.mail'].sudo().create(mail_values)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Report emailed'),
                'message': _('%d email(s) queued.') % len(mail_values),
                'type': 'success',
            },
        }

    def action_cron_email_monthly(self):
        for template in self.search([('email_monthly', '=', True)]):
            template.action_email()

    def render_csv(self):
        self.ensure_one()
        output = io.BytesIO()
        writer = pycompat.csv_writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([_('Group'), _('Gross'), _('Deductions'),
                         _('Net'), _('Lines')])
        for row in self.get_report_rows():
            writer.writerow([row['group'], row['gross'], row['deductions'],
                             row['net'], row['line_count']])
        return output.getvalue().decode()
