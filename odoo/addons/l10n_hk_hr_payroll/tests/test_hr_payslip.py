from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestHrPayslip(TransactionCase):

    def test_remove_payslip_period(self):
        """Test payroll computations when the payslip period is removed."""
        company_hk = self.env['res.company'].create({
            'name': 'HK Co',
            'country_id': self.env.ref('base.hk').id,
        })

        slip_form = Form(self.env['hr.payslip'].with_company(company_hk))
        slip_form.date_from = False

        self.assertFalse(slip_form.l10n_hk_includes_eoy_pay)
        self.assertEqual(slip_form.l10n_hk_average_daily_wage, 0.0)
