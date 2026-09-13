import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(Navbar.prototype, {
    async showRTStatus() {
        const result = await this.pos.fiscalPrinter.getRTStatus();
        if (result.success) {
            this.dialog.add(AlertDialog, {
                title: _t("RT Status"),
                body: JSON.stringify(result.addInfo, null, 4),
            });
        }
    },
});
