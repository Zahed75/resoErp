# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _


class RcloudNightAuditRun(models.TransientModel):
    """Post room charges for stays covering the business date, then
    advance the business date by one day."""

    _name = 'rcloud.night.audit.run'
    _description = 'Night Audit'

    date = fields.Date(
        required=True, default=lambda s: s._get_business_date(),
        help='Business date to audit (normally yesterday).')

    # ------------------------------------------------------ business date
    @api.model
    def _get_business_date(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'rcloud.business_date')
        return fields.Date.to_date(raw) if raw else fields.Date.today()

    @api.model
    def _set_business_date(self, date):
        self.env['ir.config_parameter'].sudo().set_param(
            'rcloud.business_date', fields.Date.to_string(date))

    # ------------------------------------------------------------- crons
    @api.model
    def cron_run(self):
        """23:55 cron: run the audit for the current business date."""
        run = self.create({'date': self._get_business_date()})
        return run.action_run()

    # ---------------------------------------------------------------- run
    def action_run(self):
        self.ensure_one()
        date = self.date
        reservations = self.env['rcloud.reservation'].sudo().search([
            ('state', '=', 'checked_in'),
            ('arrival', '<=', date),
            ('departure', '>', date),
        ])
        Folio = self.env['rcloud.folio'].sudo()
        FolioLine = self.env['rcloud.folio.line'].sudo()
        created = FolioLine
        for res in reservations:
            folio = res.folio_id
            if not folio:
                folio = Folio.create({
                    'reservation_id': res.id,
                    'partner_id': res.guest_id.id,
                })
                res.folio_id = folio
            room_name = res.room_id.name or res.room_type_id.name
            description = _('Room charge %s %s') % (room_name, date)
            if FolioLine.search_count([
                    ('folio_id', '=', folio.id),
                    ('date', '=', date),
                    ('description', '=', description),
                    ('source', '=', 'room')]):
                continue  # already posted for this night: never duplicate
            nightly = res.line_ids.filtered(lambda l: l.date == date)[:1]
            rate = nightly.rate if nightly else res.room_type_id.default_rate
            created |= FolioLine.create({
                'folio_id': folio.id,
                'date': date,
                'description': description,
                'product_id': False,
                'qty': 1,
                'unit_price': rate,
                'source': 'room',
            })
        self._set_business_date(date + timedelta(days=1))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Night Audit — Posted Room Charges'),
            'res_model': 'rcloud.folio.line',
            'domain': [('id', 'in', created.ids)],
            'view_mode': 'list,form',
            'context': {'group_by': 'folio_id'},
        }
