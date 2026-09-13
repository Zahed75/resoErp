# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.exceptions import ValidationError
from odoo.tools import SQL

# Stored fields from pos_blackbox_be on pos.session to archive
POS_SESSION_BLACKBOX_FIELDS = [
    "cash_box_opening_number",
    "pro_forma_sales_number",
    "pro_forma_sales_amount",
    "pro_forma_refund_number",
    "pro_forma_refund_amount",
    "correction_number",
    "correction_amount",
]

# Stored fields from pos_blackbox_be on pos.order to archive
POS_ORDER_BLACKBOX_FIELDS = [
    "blackbox_date",
    "blackbox_time",
    "blackbox_ticket_counters",
    "blackbox_unique_fdm_production_number",
    "blackbox_vsc_identification_number",
    "blackbox_signature",
    "blackbox_order_sequence",
    "blackbox_tax_category_a",
    "blackbox_tax_category_b",
    "blackbox_tax_category_c",
    "blackbox_tax_category_d",
    "plu_hash",
    "pos_version",
]


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _migrate_blackbox_data_v1_to_v2(self):
        self._migrate_pos_session_data()
        self._migrate_pos_order_data()
        self._migrate_res_users_insz()

    def _migrate_pos_session_data(self):
        """Move pos_blackbox_be.session fields into l10n_be_pos_blackbox.pos_session.old_pos_blackbox_be_data."""
        json_fields = SQL(", ").join(SQL("%s, %s", f, SQL.identifier(f)) for f in POS_SESSION_BLACKBOX_FIELDS)
        condition = SQL(" OR ").join(SQL("%s IS NOT NULL", SQL.identifier(f)) for f in POS_SESSION_BLACKBOX_FIELDS)
        self.env.execute_query(SQL("""
            UPDATE pos_session
            SET old_pos_blackbox_be_data = jsonb_build_object(%(json_fields)s)
            WHERE old_pos_blackbox_be_data IS NULL
            AND (%(condition)s)
            """, json_fields=json_fields, condition=condition)
        )

    def _migrate_pos_order_data(self):
        """Move pos_blackbox_be.order fields into l10n_be_pos_blackbox.pos_order.old_pos_blackbox_be_data."""
        json_fields = SQL(", ").join(SQL("%s, %s", f, SQL.identifier(f)) for f in POS_ORDER_BLACKBOX_FIELDS)
        condition = SQL(" OR ").join(SQL("%s IS NOT NULL", SQL.identifier(f)) for f in POS_ORDER_BLACKBOX_FIELDS)
        self.env.execute_query(SQL("""
            UPDATE pos_order
            SET old_pos_blackbox_be_data = jsonb_build_object(%(json_fields)s)
            WHERE old_pos_blackbox_be_data IS NULL
            AND (%(condition)s)
            """, json_fields=json_fields, condition=condition)
        )

    def _migrate_res_users_insz(self):
        """Move pos_blackbox_be.res_users insz_or_bis_number into l10n_be_insz_or_bis_number on res.users."""

        self.env.execute_query(SQL("""
            UPDATE res_users
            SET l10n_be_insz_or_bis_number = insz_or_bis_number
            WHERE insz_or_bis_number IS NOT NULL
            AND insz_or_bis_number != ''
            AND (l10n_be_insz_or_bis_number IS NULL OR l10n_be_insz_or_bis_number = '')
            """)
        )

    def _is_blackbox_v2_required(self):
        return (super()._is_blackbox_v2_required() and not self._uses_blackbox_v1()) or self._has_blackbox_v2_orders()

    def _is_blackbox_v1_required(self):
        return super()._is_blackbox_v1_required() and not self._uses_blackbox_v2()

    def _has_blackbox_v2_orders(self):
        return self.env['pos.order'].search_count([
            ('session_id.config_id', '=', self.id),
            ('l10n_be_short_signature', '!=', False),
        ], limit=1) > 0

    def _uses_blackbox_v1(self):
        return super()._uses_blackbox_v1() and not self._uses_blackbox_v2()

    def _uses_blackbox_v2(self):
        return bool(self.l10n_be_pos_id and self.l10n_be_blackbox_be_id)

    def _check_l10n_be_before_opening(self):
        super()._check_l10n_be_before_opening()
        if self.filtered(lambda config: config.certified_blackbox_identifier and config.iface_fiscal_data_module and config._uses_blackbox_v2()):
            raise ValidationError(self.env._(
                "This POS has a blackbox V1 and a blackbox V2 setup. Please remove one of the integrations before opening the session.\n"
                "If you already have made orders with the V2, you cannot go back to the V1."
            ))

    def _is_fdm_required(self):
        return super()._is_fdm_required() and not (self._is_blackbox_v2_required() or self._uses_blackbox_v2())
