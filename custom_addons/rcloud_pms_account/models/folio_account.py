# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RcloudProperty(models.Model):
    """Configuration extension: fallback revenue account for folio
    charges that carry no product."""

    _inherit = 'rcloud.property'

    income_account_id = fields.Many2one(
        'account.account', string='Folio Income Account',
        help='Revenue account used for folio charges without a product, '
             'when the product does not provide one.')


class RcloudFolio(models.Model):
    _inherit = 'rcloud.folio'

    invoice_ids = fields.One2many(
        'account.move', compute='_compute_invoice_ids',
        search='_search_invoice_ids', string='Invoices')

    @api.depends('name')
    def _compute_invoice_ids(self):
        for folio in self:
            folio.invoice_ids = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('invoice_origin', '=', folio.name),
            ])

    def _search_invoice_ids(self, operator, value):
        return [('name', operator, self.env['account.move'].browse(value).mapped('invoice_origin'))]

    def _find_invoice(self):
        """Fresh lookup (bypasses the computed-field cache)."""
        self.ensure_one()
        return self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_origin', '=', self.name),
        ], limit=1)

    # ----------------------------------------------------------- helpers
    def _analytic_distribution(self):
        """Analytic distribution dict {account_id: 100} for journal
        items, taken from the folio's property analytic account."""
        self.ensure_one()
        account = self.property_id.analytic_account_id
        return {str(account.id): 100} if account else {}

    def _accounting_company(self):
        self.ensure_one()
        return self.company_id or self.env.company

    # ------------------------------------------------------------- invoice
    def action_post_invoice(self):
        """Post ONE customer invoice covering all folio charges.

        Idempotent: a folio already invoiced returns its existing move.
        """
        self.ensure_one()
        invoice = self._find_invoice()
        if invoice:
            return invoice
        if not self.line_ids:
            raise UserError(_('The folio has no charges to invoice.'))
        company = self._accounting_company()
        distribution = self._analytic_distribution()
        prop = self.property_id
        lines = []
        for line in self.line_ids:
            line_vals = {
                'name': line.description,
                'quantity': line.qty,
                'price_unit': line.unit_price,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'analytic_distribution': distribution,
            }
            if line.product_id:
                line_vals['product_id'] = line.product_id.id
            elif prop and prop.income_account_id:
                line_vals['account_id'] = prop.income_account_id.id
            lines.append((0, 0, line_vals))
        move = self.env['account.move'].sudo().create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'company_id': company.id,
            'currency_id': self.currency_id.id or company.currency_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        })
        move.action_post()
        self.invalidate_recordset(['invoice_ids'])
        self.message_post(body=_('Invoice %s posted.') % move.name)
        return move

    # ------------------------------------------------------------- payment
    def action_apply_deposit(self, amount, journal=None):
        """Record a customer payment against this folio.

        The payment is posted; when a posted folio invoice exists, its
        outstanding receivable lines are reconciled.
        """
        self.ensure_one()
        if amount <= 0:
            raise UserError(_('Deposit amount must be positive.'))
        company = self._accounting_company()
        vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': amount,
            'company_id': company.id,
            'date': fields.Date.context_today(self),
        }
        if journal:
            vals['journal_id'] = journal.id
        payment = self.env['account.payment'].sudo().create(vals)
        payment.action_post()
        self.message_post(body=_(
            'Deposit of %s recorded (payment %s).') % (
            amount, payment.name))
        invoice = self._find_invoice()
        if invoice and invoice.state == 'posted' and \
                invoice.payment_state != 'paid':
            for line in payment.move_id.line_ids:
                if line.credit > 0 and not line.reconciled:
                    invoice.js_assign_outstanding_line(line.id)
        return payment

    def action_print_tax_invoice(self):
        self.ensure_one()
        invoice = self._find_invoice()
        if not invoice:
            raise UserError(_('Post the folio invoice first.'))
        return self.env.ref(
            'rcloud_pms_account.action_report_tax_invoice'
        ).report_action(invoice)
