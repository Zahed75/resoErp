# -*- coding: utf-8 -*-
from datetime import timedelta

from psycopg2.errors import SerializationFailure

from odoo import api, fields, models, _
from odoo.exceptions import UserError

RETRIES = 3


class RcloudAvailability(models.Model):
    """Availability bucket per property / room type / date.

    Overbooking is structurally impossible:
      * CHECK constraint `sold + blocked <= total` at the database level
      * `allocate()` takes a row lock (SELECT ... FOR UPDATE) so concurrent
        bookers serialize on the same bucket
    """

    _name = 'rcloud.availability'
    _description = 'Availability Bucket'
    _order = 'date'

    property_id = fields.Many2one(
        'rcloud.property', required=True, ondelete='cascade', index=True)
    room_type_id = fields.Many2one(
        'rcloud.room.type', required=True, ondelete='cascade', index=True)
    date = fields.Date(required=True, index=True)
    total = fields.Integer(required=True, default=0)
    sold = fields.Integer(required=True, default=0)
    blocked = fields.Integer(required=True, default=0)

    _bucket_uniq = models.Constraint(
        'unique(property_id, room_type_id, date)',
        'An availability bucket already exists for this day.')

    _no_overbooking = models.Constraint(
        'check(coalesce(sold, 0) + coalesce(blocked, 0) <= coalesce(total, 0))',
        'Overbooking is not possible: sold + blocked exceeds total rooms.')

    @api.model
    def ensure_buckets(self, property_id, room_type_id, date_from, date_to):
        """Idempotently create buckets for [date_from, date_to).

        Retried on serialization failures: under snapshot isolation an
        ``INSERT ... ON CONFLICT`` racing another commit can abort with
        ``could not serialize access due to concurrent update``.
        """
        rooms_total = self.env['rcloud.room'].sudo().search_count([
            ('room_type_id', '=', room_type_id),
        ])
        days = (date_to - date_from).days
        for i in range(days):
            day = date_from + timedelta(days=i)
            for _attempt in range(RETRIES):
                try:
                    with self.env.cr.savepoint():
                        self._create_bucket_ignore_conflict(
                            property_id, room_type_id, day, rooms_total)
                    break
                except SerializationFailure:
                    if _attempt == RETRIES - 1:
                        raise

    def _create_bucket_ignore_conflict(self, property_id, room_type_id,
                                       day, total):
        self.env.cr.execute(
            """
            INSERT INTO rcloud_availability
                (property_id, room_type_id, date, total, sold, blocked)
            VALUES (%s, %s, %s, %s, 0, 0)
            ON CONFLICT (property_id, room_type_id, date) DO NOTHING
            """, (property_id, room_type_id, day, total))

    def _lock(self):
        """Row-lock these buckets in deterministic order."""
        self.env.cr.execute(
            """
            SELECT id FROM rcloud_availability
            WHERE id IN %s ORDER BY id FOR UPDATE
            """, (tuple(self.ids),))

    def allocate(self, qty=1):
        """Lock and increment `sold`. Raises UserError when full —
        and can never oversell thanks to the CHECK constraint."""
        self.ensure_one()
        if qty < 1:
            return
        for _attempt in range(RETRIES):
            try:
                with self.env.cr.savepoint():
                    self._lock()
                    self.env.cr.execute(
                        """
                        UPDATE rcloud_availability
                        SET sold = sold + %s
                        WHERE id = %s AND sold + blocked + %s <= total
                        """, (qty, self.id, qty))
                    if self.env.cr.rowcount != 1:
                        raise UserError(
                            _('No availability left for %s on %s.') % (
                                self.room_type_id.name, self.date))
                    self.invalidate_recordset(['sold'])
                return
            except SerializationFailure:
                if _attempt == RETRIES - 1:
                    raise

    def release(self, qty=1):
        self.ensure_one()
        for _attempt in range(RETRIES):
            try:
                with self.env.cr.savepoint():
                    self._lock()
                    self.env.cr.execute(
                        "UPDATE rcloud_availability SET sold = GREATEST(sold - %s, 0) "
                        "WHERE id = %s", (qty, self.id))
                    self.invalidate_recordset(['sold'])
                return
            except SerializationFailure:
                if _attempt == RETRIES - 1:
                    raise

    def block(self, qty=1):
        self.ensure_one()
        for _attempt in range(RETRIES):
            try:
                with self.env.cr.savepoint():
                    self._lock()
                    self.env.cr.execute(
                        """
                        UPDATE rcloud_availability
                        SET blocked = blocked + %s
                        WHERE id = %s AND sold + blocked + %s <= total
                        """, (qty, self.id, qty))
                    if self.env.cr.rowcount != 1:
                        raise UserError(
                            _('Cannot block %s on %s: it is already sold.') % (
                                self.room_type_id.name, self.date))
                    self.invalidate_recordset(['blocked'])
                return
            except SerializationFailure:
                if _attempt == RETRIES - 1:
                    raise

    def unblock(self, qty=1):
        self.ensure_one()
        for _attempt in range(RETRIES):
            try:
                with self.env.cr.savepoint():
                    self._lock()
                    self.env.cr.execute(
                        "UPDATE rcloud_availability SET blocked = GREATEST(blocked - %s, 0) "
                        "WHERE id = %s", (qty, self.id))
                    self.invalidate_recordset(['blocked'])
                return
            except SerializationFailure:
                if _attempt == RETRIES - 1:
                    raise

    @api.model
    def search_buckets(self, property_id, room_type_id, date_from, date_to):
        """Read-only bucket lookup (never INSERTs — safe under REPEATABLE
        READ, where ``INSERT ... ON CONFLICT`` can abort with
        ``could not serialize access due to concurrent update``)."""
        return self.search([
            ('property_id', '=', property_id),
            ('room_type_id', '=', room_type_id),
            ('date', '>=', date_from),
            ('date', '<', date_to),
        ], order='date')

    @api.model
    def buckets_for(self, property_id, room_type_id, date_from, date_to):
        self.ensure_buckets(property_id, room_type_id, date_from, date_to)
        return self.search_buckets(property_id, room_type_id, date_from, date_to)
