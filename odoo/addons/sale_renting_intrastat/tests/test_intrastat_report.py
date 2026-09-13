from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestIntrastatReport(TestAccountReportsCommon):

    @freeze_time('2022-01-01')
    def test_rentals_in_intrastat_report_values(self):
        self.company_data['company'].country_id = self.env.ref('base.be')
        self.company_data['company'].currency_id = self.env.ref('base.EUR').id
        self.company_data['currency'] = self.env.ref('base.EUR')
        self.report = self.env.ref('account_intrastat.intrastat_report')
        self.env.company.totals_below_sections = False

        partner = self.env['res.partner'].create({
            'name': 'Spanish partner',
            'country_id': self.env.ref('base.es').id
        })

        product = self.env['product.product'].create({
            'name': 'Projector',
            'rent_ok': True,
        })
        recurrence_yearly = self.env['sale.temporal.recurrence'].sudo().create({'duration': 1.0, 'unit': 'year'})
        self.env['product.pricing'].sudo().create({
            'product_template_id': product.product_tmpl_id.id,
            'recurrence_id': recurrence_yearly.id,
            'price': 120,
        })

        # 1 year rental
        so_1_year = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'rental_start_date': '2022-01-01',
            'rental_return_date': '2023-01-01',
        })
        self.env['sale.order.line'].sudo().create({
            'product_id': product.id,
            'order_id': so_1_year.id,
            'is_rental': True,
        })

        # 2 year rental
        so_2_years = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'rental_start_date': '2022-01-01',
            'rental_return_date': '2024-01-01',
        })
        self.env['sale.order.line'].sudo().create({
            'product_id': product.id,
            'order_id': so_2_years.id,
            'is_rental': True,
        })

        # 3 year rental
        so_3_years = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'rental_start_date': '2022-01-01',
            'rental_return_date': '2025-01-01',
        })
        self.env['sale.order.line'].sudo().create({
            'product_id': product.id,
            'order_id': so_3_years.id,
            'is_rental': True,
        })

        orders = so_1_year | so_2_years | so_3_years
        orders.action_confirm()

        invoice = orders._create_invoices()

        # An invoice line may be linked to several sale order lines. Such additional links must not duplicate
        # its Intrastat values. If not handled, this will cause so_2_years to be duplicated, adding 240 to the reported value.
        two_year_invoice_line = invoice.invoice_line_ids.filtered(
            lambda line: so_2_years.order_line in line.sale_line_ids
        )
        two_year_invoice_line.sale_line_ids += so_3_years.order_line

        invoice.action_post()

        options = self._generate_options(self.report, '2022-01-01', '2025-12-31')
        lines = self.report._get_lines(options)

        # Only the 2-year and 3-year rental should appear. The 1-year rental should not appear
        expected_intrastat_value = so_2_years.amount_total + so_3_years.amount_total
        self.assertLinesValues(
            lines,
            # 1/system, 2/country code, 12/value
            [1, 2, 12],
            [
                ('', '', expected_intrastat_value),
                # account.move (invoice) 1
                ('29 (Dispatch)', 'Spain', expected_intrastat_value),
            ],
            options,
        )
