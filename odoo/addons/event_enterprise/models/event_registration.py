# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # store it to be able to group_by (event_begin_date in cohort view)
    event_begin_date = fields.Datetime(store=True)

    # corrected dependencies because field was made store for cohort view
    @api.depends("event_id.date_begin", "event_slot_id.start_datetime")
    def _compute_event_begin_date(self):
        super()._compute_event_begin_date()
