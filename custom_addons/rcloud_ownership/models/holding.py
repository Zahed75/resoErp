# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RcloudShareHolding(models.Model):
    """Append-only acquisition record.

    A holding row represents units ACQUIRED on acquired_date. Reductions
    and onward movements are never written onto the row — they are
    rcloud.share.transfer events. A position on any date is therefore
    replayed as: acquisitions (holding rows, +units) plus completed
    transfers into (+units) / out of (-units) the owner, all dated on or
    before the requested date.
    """

    _name = 'rcloud.share.holding'
    _description = 'Share Holding'
    _order = 'share_class_id, acquired_date, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'certificate_number'

    owner_id = fields.Many2one(
        'rcloud.owner', required=True, ondelete='cascade', index=True)
    share_class_id = fields.Many2one(
        'rcloud.share.class', required=True, ondelete='restrict', index=True)
    company_id = fields.Many2one(
        related='share_class_id.company_id', store=True, index=True,
        string='Company')
    units_held = fields.Integer(
        string='Units Acquired', required=True,
        help='Units acquired on the acquisition date. See model docstring '
             'for why rows are append-only.')
    acquired_date = fields.Date(required=True, default=fields.Date.today)
    certificate_number = fields.Char(
        readonly=True, copy=False, default='New')
    state = fields.Selection([
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ], default='active', required=True, tracking=True,
        help='Cancelled rows are excluded from position replays.')

    _holding_uniq = models.Constraint(
        'unique(owner_id, share_class_id)',
        'An owner can hold only one acquisition record per share class; '
        'increases must be modelled as transfers.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('certificate_number', 'New') == 'New':
                vals['certificate_number'] = self.env['ir.sequence'].next_by_code(
                    'rcloud.share.certificate') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------- position replay
    @api.model
    def _signed_events(self, owner, share_class, date_to=None):
        """Acquisition (+) and completed transfer (+/-) events."""
        domain = [
            ('owner_id', '=', owner.id),
            ('share_class_id', '=', share_class.id),
            ('state', '=', 'active'),
        ]
        if date_to:
            domain.append(('acquired_date', '<=', date_to))
        events = [(h.acquired_date, h.units_held)
                  for h in self.search(domain)]
        Transfer = self.env['rcloud.share.transfer'].sudo()
        base = [('share_class_id', '=', share_class.id),
                ('state', '=', 'completed')]
        if date_to:
            base.append(('transfer_date', '<=', date_to))
        events += [(t.transfer_date, -t.units)
                   for t in Transfer.search(base + [('from_owner_id', '=', owner.id)])]
        events += [(t.transfer_date, t.units)
                   for t in Transfer.search(base + [('to_owner_id', '=', owner.id)])]
        return events

    @api.model
    def get_holding_on(self, owner, share_class, date):
        """Units held by owner on the given date (inclusive)."""
        return sum(units for _d, units in
                   self._signed_events(owner, share_class, date))

    @api.model
    def get_weighted_units(self, owner, share_class, date_from, date_to):
        """Unit-days over [date_from, date_to): every signed event
        contributes its units times the days it was held within the
        period."""
        total = 0.0
        for event_date, units in self._signed_events(
                owner, share_class, date_to):
            effective = max(event_date, date_from)
            days = (date_to - effective).days
            if days > 0:
                total += units * days
        return total
