# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools import SQL, Query


class BudgetReport(models.Model):
    _inherit = 'budget.report'

    line_type = fields.Selection(selection_add=[('committed', 'Committed')])
    committed = fields.Float('Committed', readonly=True)

    def _get_pol_query(self, plan_fnames):
        budget_line_domain = self.env.context.get('budget_line_domain') or []
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit')
        qty_invoiced_table = SQL(
            """
               SELECT SUM(
                          CASE WHEN COALESCE(uom_aml.id != uom_pol.id, FALSE)
                               THEN ROUND(CAST((aml.quantity / uom_aml.factor) * uom_pol.factor AS NUMERIC), %(precision_digits)s)
                               ELSE COALESCE(aml.quantity, 0)
                          END
                          * CASE WHEN am.move_type = 'in_invoice' THEN 1
                                 WHEN am.move_type = 'in_refund' THEN -1
                                 ELSE 0 END
                      ) AS qty_invoiced,
                      pol.id AS pol_id
                 FROM purchase_order po
            LEFT JOIN purchase_order_line pol ON pol.order_id = po.id
            LEFT JOIN account_move_line aml ON aml.purchase_line_id = pol.id
            LEFT JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN uom_uom uom_aml ON uom_aml.id = aml.product_uom_id
            LEFT JOIN uom_uom uom_pol ON uom_pol.id = pol.product_uom_id
                WHERE aml.parent_state = 'posted'
             GROUP BY pol.id
        """,
            precision_digits=precision_digits,
        )

        def get_query(bl_join, bl_condition):
            query = Query(self.env, alias='pol', table=SQL.identifier('purchase_order_line'))
            query.add_join('LEFT JOIN', 'qty_invoiced_table', SQL("(%s)", qty_invoiced_table), SQL("qty_invoiced_table.pol_id = pol.id"))
            query.add_join('JOIN', 'po', 'purchase_order', SQL("pol.order_id = po.id AND po.state = 'purchase'"))
            query.add_join('JOIN', 'a', SQL(
                """LATERAL (
                    SELECT rate, %(analytic_columns)s
                      FROM JSONB_TO_RECORDSET(pol.analytic_json) AS x(rate FLOAT, %(field_cast)s)
                )""",
                analytic_columns=SQL(', ').join(SQL.identifier(fname) for fname in plan_fnames),
                field_cast=SQL(', ').join(SQL('%s FLOAT', SQL.identifier(fname)) for fname in plan_fnames),
            ), SQL("TRUE"))
            query.add_join(bl_join, 'bl', 'budget_line', bl_condition)
            query.add_join('LEFT JOIN', 'ba', 'budget_analytic', SQL("ba.id = bl.budget_analytic_id"))
            return query

        select_columns = [
            "(pol.id::TEXT || '-' || ROW_NUMBER() OVER (PARTITION BY pol.id ORDER BY pol.id)) AS id",
            "bl.budget_analytic_id AS budget_analytic_id",
            "bl.id AS budget_line_id",
            "'purchase.order' AS res_model",
            "po.id AS res_id",
            "po.date_order AS date",
            "pol.name AS description",
            "pol.company_id AS company_id",
            "po.user_id AS user_id",
            "'committed' AS line_type",
            "0 AS budget",
            """COALESCE(pol.price_subtotal::FLOAT, pol.price_unit::FLOAT * pol.product_qty)
                / COALESCE(NULLIF(pol.product_qty, 0), 1)
                * (pol.product_qty - COALESCE(qty_invoiced_table.qty_invoiced, 0))
                / po.currency_rate
                * (a.rate)
                * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END AS committed""",
            "0 AS achieved",
            "0 AS theoretical",
            *(self.env['account.analytic.line']._field_to_sql('a', fname) for fname in plan_fnames),
        ]

        budget_lines = self.env['budget.line'].sudo().search(budget_line_domain)
        shape2budget_lines = budget_lines._by_shape()

        # Q1 - PO lines matched to a null-company budget line.
        # Q2 - PO lines matched to a company-specific budget line.
        company_conditions = [
            SQL('bl.company_id IS NULL'),
            SQL('po.company_id = bl.company_id'),
        ]

        queries = []
        for company_condition in company_conditions:
            for shape, line_ids in shape2budget_lines.items():
                query = get_query('JOIN', SQL(
                    """
                        %(company_condition)s
                        AND po.date_order >= bl.date_from
                        AND date_trunc('day', po.date_order) <= bl.date_to
                        AND bl.id = ANY(%(ids)s)
                        AND %(shape_join)s
                    """,
                    company_condition=company_condition,
                    ids=line_ids.ids,
                    shape_join=self._shape_join('budget.line', 'a', 'budget.line', 'bl', shape),
                ))
                query.add_where(SQL("pol.product_qty > COALESCE(qty_invoiced_table.qty_invoiced, 0)"))
                query.add_where(SQL("ba.budget_type != 'revenue'"))
                queries.append(query.select(*select_columns))

        return SQL(' UNION ALL ').join(queries)

    @property
    def _table_query(self):
        self.env['purchase.order'].flush_model()
        self.env['purchase.order.line'].flush_model()
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        plan_fnames = [plan._column_name() for plan in project_plan | other_plans]
        return SQL(" UNION ALL ").join(filter(None, (
            super()._table_query,
            self._get_pol_query(plan_fnames),
        )))
