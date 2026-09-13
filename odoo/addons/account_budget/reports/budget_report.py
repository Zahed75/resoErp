# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.fields import Domain
from odoo.tools import SQL, Query


class BudgetReport(models.Model):
    _name = 'budget.report'
    _inherit = ['analytic.plan.fields.mixin']
    _description = "Budget Report"
    _auto = False
    _order = 'date desc'

    date = fields.Date('Date')
    res_model = fields.Char('Model', readonly=True)
    res_id = fields.Many2oneReference('Document', model_field='res_model', readonly=True)
    description = fields.Char('Description', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    line_type = fields.Selection([('budget', 'Budget'), ('achieved', 'Achieved')], 'Type', readonly=True)
    budget = fields.Float('Budget', readonly=True)
    achieved = fields.Float('Achieved', readonly=True)
    theoretical = fields.Float(readonly=True)
    budget_analytic_id = fields.Many2one('budget.analytic', 'Budget Analytic', readonly=True)
    budget_line_id = fields.Many2one('budget.line', 'Budget Line', readonly=True)

    def _shape_join(self, model1, alias1, model2, alias2, shape):
        plan_fnames = self._get_plan_fnames()
        return SQL(' AND ').join([
            SQL(
                "%(model1)s = %(model2)s",
                model1=self.env[model1]._field_to_sql(alias1, fname),
                model2=self.env[model2]._field_to_sql(alias2, fname),
            )
            for fname, is_set in zip(plan_fnames, shape)
            if is_set
        ]) or SQL('TRUE')

    def _get_bl_query(self, plan_fnames):
        budget_line_domain = self.env.context.get('budget_line_domain')
        return SQL(
            """
            SELECT CONCAT('bl', bl.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'budget.analytic' AS res_model,
                   bl.budget_analytic_id AS res_id,
                   bl.date_from AS date,
                   ba.name AS description,
                   bl.company_id AS company_id,
                   NULL AS user_id,
                   'budget' AS line_type,
                   bl.budget_amount AS budget,
                   0 AS committed,  -- used in `account_budget_purchase`
                   0 AS achieved,
                   CASE WHEN %(today)s BETWEEN bl.date_from AND bl.date_to
                        THEN (((%(today)s::DATE - bl.date_from::DATE + 1)) / (bl.date_to::DATE - bl.date_from::DATE + 1)::FLOAT) * bl.budget_amount
                        WHEN %(today)s < bl.date_from
                        THEN 0
                        ELSE bl.budget_amount
                   END AS theoretical,
                   %(plan_fields)s
              FROM budget_line bl
              JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
              %(budget_line_condition)s
            """,
            plan_fields=SQL(', ').join(self.env['budget.line']._field_to_sql('bl', fname) for fname in plan_fnames),
            budget_line_condition=SQL('WHERE %s', budget_line_domain._to_sql(self, 'bl', None)) if budget_line_domain else SQL(''),
            today=fields.Date.context_today(self),
        )

    def _get_aal_query(self, plan_fnames):
        def get_query(bl_join, bl_condition):
            query = Query(self.env, alias='aal', table=SQL.identifier('account_analytic_line'))
            query.add_join(bl_join, 'bl', 'budget_line', bl_condition)
            query.add_join('LEFT JOIN', 'ba', 'budget_analytic', SQL("ba.id = bl.budget_analytic_id"))
            return query

        budget_line_domain = self.env.context.get('budget_line_domain') or []

        # For performance reasons, we split the query into 3 parts and then UNION ALL the results
        # (faster than doing a single query with an OR on the left join condition):
        # Q1 - analytic lines with no matching budget line at all.
        # Q2 - analytic lines matched to a null-company budget line.
        # Q3 - analytic lines matched to a company-specific budget line.

        select_columns = [
            "CONCAT('aal', aal.id::TEXT) AS id",
            "bl.budget_analytic_id AS budget_analytic_id",
            "bl.id AS budget_line_id",
            "'account.analytic.line' AS res_model",
            "aal.id AS res_id",
            "aal.date AS date",
            "aal.name AS description",
            "aal.company_id AS company_id",
            "aal.user_id AS user_id",
            "'achieved' AS line_type",
            "0 AS budget",
            "aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS committed",  # used in `account_budget_purchase`
            "aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS achieved",
            "0 AS theoretical",
            *(self.env['account.analytic.line']._field_to_sql('aal', fname) for fname in plan_fnames),
        ]

        def where_account_type(query):
            query.add_join('LEFT JOIN', 'aa', 'account_account', SQL("aa.id = aal.general_account_id"))
            return SQL("""(
                SPLIT_PART(aa.account_type, '_', 1) IN ('income', 'expense')
                OR aa.account_type IN ('asset_current', 'asset_non_current', 'asset_fixed')
                OR aa.account_type IS NULL
            )""")

        budget_lines = self.env['budget.line'].sudo().search(budget_line_domain)

        # Group budget lines by the shape of their plan fields to optimize the query
        # For each budget line, we only care which fields are set, not their specific values.
        shape2budget_lines = budget_lines._by_shape()

        queries = []

        # Q1 - analytic lines with no matching budget line at all.
        if not budget_line_domain:
            query = get_query('LEFT JOIN', SQL("FALSE"))
            # filter it so that we only get the aals that have no bl
            if shape2budget_lines:
                query.add_where(SQL(
                    "NOT EXISTS (SELECT 1 FROM (%(union)s) matched_aal WHERE matched_aal.id = aal.id)",
                    union=SQL(' UNION ALL ').join([
                        get_query('JOIN', SQL(
                            """
                                aal.date >= bl.date_from
                                AND aal.date <= bl.date_to
                                AND bl.id = ANY(%(ids)s)
                                AND %(shape_join)s
                            """,
                            ids=line_ids.ids,
                            shape_join=self._shape_join('account.analytic.line', 'aal', 'budget.line', 'bl', shape),
                        )).select("DISTINCT aal.id")
                        for shape, line_ids in shape2budget_lines.items()
                    ])
                ))
            query.add_where(where_account_type(query))
            queries.append(query.select(*select_columns))

        # Q2 - analytic lines matched to a null-company budget line.
        # Q3 - analytic lines matched to a company-specific budget line.
        company_conditions = [
            SQL('bl.company_id IS NULL'),
            SQL('aal.company_id = bl.company_id'),
        ]

        for company_condition in company_conditions:
            for shape, line_ids in shape2budget_lines.items():
                query = get_query('JOIN', SQL(
                    """
                        %(company_condition)s
                        AND aal.date >= bl.date_from
                        AND aal.date <= bl.date_to
                        AND bl.id = ANY(%(ids)s)
                        AND %(shape_join)s
                    """,
                    company_condition=company_condition,
                    ids=line_ids.ids,
                    shape_join=self._shape_join('account.analytic.line', 'aal', 'budget.line', 'bl', shape),
                ))
                query.add_where(SQL(
                    """CASE
                        WHEN ba.budget_type = 'expense' THEN ((%(profitability)s) = 'loss')
                        WHEN ba.budget_type = 'revenue' THEN ((%(profitability)s) = 'revenue')
                        ELSE TRUE
                    END""",
                    profitability=self.env['account.analytic.line']._field_to_sql('aal', 'analytic_profitability', query),
                ))
                query.add_where(where_account_type(query))
                queries.append(query.select(*select_columns))

        return SQL(' UNION ALL ').join(queries)

    @property
    def _table_query(self):
        self.env['account.move.line'].flush_model()
        self.env['budget.line'].flush_model()
        self.env['account.analytic.line'].flush_model()
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        plan_fnames = [
            fname
            for plan in project_plan | other_plans
            if (fname := plan._column_name()) in self
        ]
        return SQL(" UNION ALL ").join(filter(None, (
            self._get_bl_query(plan_fnames),
            self._get_aal_query(plan_fnames),
        )))

    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        budget_line_domain = Domain(domain).map_conditions(lambda cond: (
            cond if cond.field_expr == 'budget_analytic_id'
            else Domain('id', cond.operator, cond.value) if cond.field_expr == 'budget_line_id'
            else fields.Domain.TRUE
        )).optimize_full(self.env['budget.line'])
        return super(BudgetReport, self.with_context(budget_line_domain=budget_line_domain))._search(
            domain, offset=offset, limit=limit, order=order, active_test=active_test, bypass_access=bypass_access,
        )

    def action_open_reference(self):
        self.ensure_one()
        if self.res_model == 'account.analytic.line':
            analytical_line = self.env['account.analytic.line'].browse(self.res_id)
            if analytical_line.move_line_id:
                return analytical_line.move_line_id.action_open_business_doc()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
        }
