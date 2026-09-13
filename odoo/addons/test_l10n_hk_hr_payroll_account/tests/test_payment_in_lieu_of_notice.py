# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY

from odoo.tests import tagged

from .common import TestL10NHkHrPayrollAccountCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPaymentInLieuOfNotice(TestL10NHkHrPayrollAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract.write({
            'date_version': date(2022, 1, 1),
            'contract_date_start': date(2022, 1, 1),
            'contract_date_end': date(2023, 4, 21),
        })

    def test_regular(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 20200.0,
            'NET': 20200.0,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_lieu_of_notice_period(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id,
            input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_lieu_of_notice_period').id, 'amount': 2})])
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 40400.0,
            'NET': 40400.0,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_incomplete_year(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2023, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 20480.56,
            'NET': 20480.56,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_commission(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31),
                                             input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 30200.0,
            'NET': 30200.0,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_unpaid_and_non_full_pay_leave(self):
        leaves_to_create = [
            (datetime(2023, 2, 21), datetime(2023, 2, 22), self.env.ref('hr_holidays.l10n_hk_leave_type_unpaid_leave')),
            (datetime(2023, 3, 13), datetime(2023, 3, 15), self.env.ref('hr_holidays.l10n_hk_leave_type_sick_leave_80')),
        ]
        for date_from, date_to, leave_type in leaves_to_create:
            self._generate_leave(date_from, date_to, leave_type)
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id)
        result = {
            'PAYMENT_IN_LIEU_OF_NOTICE': 20195.12,
            'NET': 20195.12,
        }
        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self._validate_payslip(payslip, result)

    def test_short_employment(self):
        """ Test the payment in lieu of notice for a short employment. """
        # For one month of employment, if given one month of payment in lieu of notice, we should see exactly one month of wage.
        self.contract.write({
            'date_version': date(2026, 7, 1),
            'contract_date_start': date(2026, 7, 1),
            'contract_date_end': date(2026, 8, 1),
            'wage': 10000,
            'l10n_hk_internet': 0.0,
        })
        payslip = self._generate_payslip(date(2026, 7, 1), date(2026, 7, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        pil_payslip = self._generate_payslip(
            date(2026, 8, 1), date(2026, 8, 31),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id,
        )
        self._validate_payslip(pil_payslip, {
            'PAYMENT_IN_LIEU_OF_NOTICE': 10000.00,
            'NET': 10000.00,
        })

    def test_short_employment_with_unpaid_leave(self):
        """ Test payment in lieu of notice for < 1 year employment WITH unpaid leave. """
        self.contract.write({
            'date_version': date(2026, 5, 1),
            'contract_date_start': date(2026, 5, 1),
            'contract_date_end': date(2026, 8, 1),
            'wage': 10000,
            'l10n_hk_internet': 0.0,
        })

        # Create 5 days of unpaid leave in June
        self._generate_leave(
            datetime(2026, 6, 14),
            datetime(2026, 6, 18),
            self.env.ref('hr_holidays.l10n_hk_leave_type_unpaid_leave'),
        )

        # Generate May, June, July payslips
        for dt in rrule(MONTHLY, dtstart=datetime(2026, 5, 1), until=datetime(2026, 7, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

        pil_payslip = self._generate_payslip(
            date(2026, 8, 1), date(2026, 8, 31),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id,
        )
        self._validate_payslip(pil_payslip, {
            'PAYMENT_IN_LIEU_OF_NOTICE': 9987.23,
            'NET': 9987.23,
        })

    def test_custom_average_monthly_wage(self):
        for dt in rrule(MONTHLY, dtstart=datetime(2022, 1, 1), until=datetime(2023, 4, 1)):
            payslip = self._generate_payslip(dt.date(), dt.date() + relativedelta(day=31))
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

        payslip = self._generate_payslip(
            date(2023, 4, 1), date(2023, 4, 30),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id,
            input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_custom_average_monthly_salary').id, 'amount': 50000})],
        )
        self._validate_payslip(payslip, {
            'PAYMENT_IN_LIEU_OF_NOTICE': 50000.0,
            'NET': 50000.0,
        })

    def test_short_employment_mid_month(self):
        """ Test a short employment starting in the middle of two months """
        self.contract.write({
            'date_version': date(2026, 6, 15),
            'contract_date_start': date(2026, 6, 15),
            'contract_date_end': date(2026, 8, 1),
            'wage': 10000,
            'l10n_hk_internet': 0.0,
        })
        payslips = self._generate_payslip(date(2026, 6, 1), date(2026, 6, 30))
        payslips |= self._generate_payslip(date(2026, 7, 1), date(2026, 7, 31))
        payslips.action_payslip_done()
        payslips.action_payslip_paid()
        pil_payslip = self._generate_payslip(
            date(2026, 8, 1), date(2026, 8, 31),
            struct_id=self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_payment_in_lieu_of_notice').id,
        )
        self._validate_payslip(pil_payslip, {
            'PAYMENT_IN_LIEU_OF_NOTICE': 9835.97,
            'NET': 9835.97,
        })
