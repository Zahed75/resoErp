import requests
from markupsafe import Markup

from odoo import Command, fields, models
from odoo.exceptions import RedirectWarning, UserError


class AccountReturn(models.Model):
    _inherit = 'account.return'

    l10n_de_elster_payload_attachment_id = fields.Many2one(comodel_name='ir.attachment')

    def _proceed_with_submission(self):
        res = super()._proceed_with_submission()
        if self.type_external_id == 'l10n_de_reports.de_tax_return_type':
            self._l10n_de_reports_elster_action_submit()
        return res

    def _reset_common(self):
        super()._reset_common()
        self.l10n_de_elster_payload_attachment_id = False

    def _link_l10n_de_elster_payload_attachment_id(self, data):
        self.l10n_de_elster_payload_attachment_id = self.env['ir.attachment'].sudo().create({
            'name': data['file_name'],
            'mimetype': 'application/xml',
            'raw': data['file_content'],
            'res_model': self._name,
            'res_id': self.id,
        })
        self.message_post(
            body=self.env._("The tax report's XML has been attached. You can review it before submission."),
            attachment_ids=self.l10n_de_elster_payload_attachment_id.ids,
        )

    def _generate_locking_attachments(self, options):
        super()._generate_locking_attachments(options)
        if self.type_external_id == 'l10n_de_reports.de_tax_return_type':
            data = self.type_id.report_id.dispatch_report_action(options, 'export_tax_report_to_xml')
            self._link_l10n_de_elster_payload_attachment_id(data)

    def _l10n_de_reports_elster_get_payload_xml(self, report, options):
        if not self.l10n_de_elster_payload_attachment_id:
            data = self.env[report.custom_handler_model_name].export_tax_report_to_xml(options)
            self._link_l10n_de_elster_payload_attachment_id(data)
        return self.l10n_de_elster_payload_attachment_id.raw.decode('iso-8859-1')

    def _l10n_de_reports_elster_get_company_tax_number(self, company):
        if not (tax_number := company.get_l10n_de_stnr_national()):
            raise RedirectWarning(
                self.env._("Your company's must have a SteuerNummer. Please configure it before submitting to ELSTER."),
                company._get_records_action(),
                self.env._("Configure your company"),
            )
        return tax_number

    def _l10n_de_reports_elster_action_submit(self):
        self.ensure_one()

        report = self.type_id.report_id
        options = report.get_options({'date': {'date_from': str(self.date_from), 'date_to': str(self.date_to)}})
        company = report._get_sender_company_for_export(options)
        payload_xml = self._l10n_de_reports_elster_get_payload_xml(report, options)
        config_params = self.env['ir.config_parameter'].sudo()
        db_uuid = config_params.get_param('database.uuid')
        send_mode = config_params.get_param('l10n_de_reports_elster.elster_proxy_mode', 'prod')

        payload = {
            'report_content':  payload_xml,
            'send_mode': send_mode,
            'tax_number': self._l10n_de_reports_elster_get_company_tax_number(company),
        }

        proxy_url = config_params.get_param(
            'l10n_de_reports_elster.elster_proxy_url',
            'https://l10n-de-elster.api.odoo.com',
        ).rstrip('/')

        try:
            response = requests.post(
                url=f'{proxy_url}/api/l10n_de_elster/1/submit',
                params={'db_uuid': db_uuid},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            raise UserError(self.env._("Submission Failed, Please try again later"))
        result = response.json()
        self._l10n_de_reports_elster_process_response(result)

    def _l10n_de_reports_elster_process_response(self, result):

        if 'error' in result:
            error = result['error']
            msg = self.env._("Submission failed with error code: %s", result['error']['eric_code'])
            if error_list := [validation_error.get('message', '') for validation_error in error.get('validation_errors', [])]:
                msg += self.env._("\n\nDetails:\n") + "\n".join(error_list)
            msg += self.env._("\n\nFor complete error code reference, check out https://docs.rs/eric-sdk/latest/eric_sdk/enum.ErrorCode.html.")
            raise UserError(msg)

        messages = [Markup("<strong>%s</strong>") % self.env._("Successfully submitted to Elster.")]
        if ticket := result['transfer_ticket']:
            messages.append(Markup("<br/>%s") % self.env._("Transfer Ticket: %s", ticket))
        if hints := result.get('hints'):
            messages.append(Markup("<br/><em>%s</em>") % self.env._("Hints:"))
            hint_items = [Markup("<li>[%s] %s</li>") % (h.get('field', ''), h.get('message', '')) for h in hints]
            messages.append(Markup("<ul>%s</ul>") % Markup("").join(hint_items))

        period = f'{self.date_to.year}_{self.date_to.month}'

        if pdf_b64 := result['pdf_confirmation']:
            attachment = self.env['ir.attachment'].sudo().create({
                'name': f'ELSTER_Uebertragungsprotokoll_{period}.pdf',
                'datas': pdf_b64,
                'type': 'binary',
                'res_model': self._name,
                'res_id': self.id,
            })
            self.attachment_ids = [Command.link(attachment.id)]

        self.message_post(body=Markup("").join(messages))
