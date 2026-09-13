import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";

export class BankRecReconcileDialogListController extends ListController {
    static template = "account_accountant.BankRecReconcileDialogListView";
    static props = {
        ...ListController.props,
        bankRecInfo: { type: Object, optional: true },
    };

    async onSelectionChanged() {
        this.props.bankRecInfo.onSelectionChanged(this);
    }
}

export class BankRecReconcileDialogListRenderer extends ListRenderer {
    static template = "account_accountant.BankRecReconcileDialogListRenderer";
    static recordRowTemplate = "account_accountant.BankRecReconcileDialogListRenderer.RecordRow";
    static props = [...ListRenderer.props, "bankRecInfo?"];

    setup() {
        super.setup();
        if (this.props.bankRecInfo?.state) {
            this.bankRecState = useState(this.props.bankRecInfo.state);
        }
    }

    async openMoveView(record) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: record.data.move_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

export const bankRecReconcileDialogListRenderer = {
    ...listView,
    Renderer: BankRecReconcileDialogListRenderer,
    Controller: BankRecReconcileDialogListController,
    props: (genericProps, view) => {
        const baseProps = listView.props(genericProps, view);
        return {
            ...baseProps,
            bankRecInfo: genericProps.bankRecInfo,
        };
    },
};

registry.category("views").add("bank_rec_dialog_list", bankRecReconcileDialogListRenderer);
