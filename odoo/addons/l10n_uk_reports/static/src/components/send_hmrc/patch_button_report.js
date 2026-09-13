/** @odoo-module */
import { AccountReportController } from "@account_reports/components/account_report/controller";
import { retrieveHMRCClientInfo } from "../../hmrc_api";

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(AccountReportController.prototype, {
    buttonAction(ev, button) {
        const additionalContext = {client_data: retrieveHMRCClientInfo()}
        if (button.client_tag == 'send_hmrc_button_report') {
            this.reportAction(ev, button.action, button.action_param, true, additionalContext);
        }
        else if (button.client_tag == 'dialog_apply_tax_unit') {
            this.env.services.dialog.add(ConfirmationDialog, {
                title: _t("Invalid Operation"),
                body: _t(
                    "%(company)s is a member of a Tax Unit. Only VAT report of the whole tax unit can be sent to HMRC.",
                    { company: user.activeCompany.name }
                ),
                confirmLabel: _t("Select Tax Unit"),
                cancelLabel: _t("Discard"),
                confirm: () => {
                    this.updateOption("tax_unit", this.options.available_tax_units[0].id);
                    this.saveSessionOptions(this.options);

                    // force the company to those impacted by the tax units, the reload will be force by this function
                    user.activateCompanies(this.options.available_tax_units[0].company_ids);
                },
                cancel: () => {
                },
            });
        }
        else {
            super.buttonAction(ev, button);
        }
    }
})
