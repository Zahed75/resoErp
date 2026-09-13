from collections import defaultdict

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import date_utils, float_round
from odoo.tools.xml_utils import cleanup_xml_node


class L10nPlVatEuReportCustomHandler(models.AbstractModel):
    _name = 'l10n_pl.vat.eu.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Polish VAT-UE Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        def tags(xmlid):
            return tuple(self.env.ref(xmlid)._get_matching_tags().ids)

        options['sales_report_taxes'] = {
            'goods': tags('l10n_pl.account_tax_report_line_dostawa_towarow_tag'),
            'triangular': tags('l10n_pl.account_tax_report_line_triangular_2nd_payer_tag'),
            'services': tags('l10n_pl.account_tax_report_line_uslugi_art_100_1_4_tag'),
            'acquisitions': tags('l10n_pl.account_tax_report_line_nabycie_towarow_tag'),
            'triangular_acquisitions': tags('l10n_pl.account_tax_report_line_triangular_buyer_2nd_payer_tag'),
        }
        options['ec_tax_filter_selection'] = [
            {'id': key, 'name': name, 'selected': True}
            for key, name in (
                ('goods', _('Supplies of goods')),
                ('triangular', _('Triangular supplies')),
                ('services', _('Supplies of services')),
                ('acquisitions', _('Acquisitions of goods')),
                ('triangular_acquisitions', _('Triangular acquisitions')),
            )
        ]
        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_pl_export_vat_eu_to_xml',
            'file_export_type': _('XML'),
        })

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        amount_keys = ('goods', 'triangular', 'services', 'acquisitions', 'triangular_acquisitions')
        lines = []
        totals = {column_group_key: defaultdict(float) for column_group_key in options['column_groups']}
        for partner, results in self._query_partners(report, options, warnings):
            partner_values = defaultdict(dict)
            for column_group_key in options['column_groups']:
                values = results.get(column_group_key, {})
                amounts = {
                    key: values.get(key, 0.0) * (-1 if key in ('acquisitions', 'triangular_acquisitions') else 1)
                    for key in amount_keys
                }
                amounts['goods'] -= amounts['triangular']
                partner_values[column_group_key].update({
                    'country_code': values.get('country_code', ''),
                    'vat_number': values.get('vat_number', ''),
                    **amounts,
                })
                for key in amount_keys:
                    totals[column_group_key][key] += partner_values[column_group_key][key]
            lines.append((0, self._get_report_line_partner(report, options, partner, partner_values)))

        if lines:
            lines.append((0, self._get_report_line_total(report, options, totals)))
        return lines

    def _get_xml_rows(self, options):
        rows_by_partner_vat = {}
        column_group_key = next(iter(options['column_groups']), None)
        if column_group_key is None:
            return []
        for partner, results in self._query_partners(self.env['account.report'].browse(options['report_id']), options):
            values = results.get(column_group_key, {})
            country_code = values.get('country_code') or ''
            vat_number = values.get('vat_number') or ''
            if not country_code or not vat_number:
                raise UserError(_('A valid EU VAT number is required for partner %s.', partner.display_name))
            row = rows_by_partner_vat.setdefault((country_code, vat_number), {
                'country_code': country_code,
                'vat_number': vat_number,
                'goods': 0.0,
                'triangular': 0.0,
                'services': 0.0,
                'acquisitions': 0.0,
                'triangular_acquisitions': 0.0,
            })
            row['goods'] += values.get('goods', 0.0) - values.get('triangular', 0.0)
            row['triangular'] += values.get('triangular', 0.0)
            row['services'] += values.get('services', 0.0)
            row['acquisitions'] -= values.get('acquisitions', 0.0)
            row['triangular_acquisitions'] -= values.get('triangular_acquisitions', 0.0)
        return list(rows_by_partner_vat.values())

    def l10n_pl_export_vat_eu_to_xml(self, options):
        company = self.env.company
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        if date_from != date_utils.start_of(date_from, 'month') or date_to != date_utils.end_of(date_from, 'month'):
            raise UserError(_('The VAT-UE declaration must cover a single calendar month.'))
        if not company.vat or not company.l10n_pl_reports_tax_office_id:
            action = self.env.ref('base.action_res_company_form')
            raise RedirectWarning(
                _('Configure the company VAT number and tax office before exporting VAT-UE.'),
                action.id,
                _('Configure your company'),
            )
        if not company.partner_id.is_company:
            raise UserError(_('VAT-UE XML export for natural persons is not supported yet.'))

        report = self.env['account.report'].browse(options['report_id'])
        report._init_currency_table(options)
        rows = self._get_xml_rows(options)
        content = self.env['ir.qweb']._render('l10n_pl_reports_vat_eu.vat_eu_export', {
            'tax_office_code': company.l10n_pl_reports_tax_office_id.code,
            'taxpayer_nip': ''.join(character for character in company.vat if character.isdigit()),
            'taxpayer_name': company.name,
            'year': date_to.year,
            'month': date_to.month,
            'rows': rows,
            'float_round': float_round,
        })
        xml = cleanup_xml_node(content, remove_blank_nodes=bool(rows))
        default_filename = report.get_default_report_filename(options, 'xml')
        return {
            'file_name': f"{default_filename.removesuffix('.xml')}_{date_to:%Y_%m}.xml",
            'file_content': etree.tostring(
                xml,
                xml_declaration=True,
                encoding='UTF-8',
            ),
            'file_type': 'xml',
        }
