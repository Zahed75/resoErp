import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class RefreshButton extends Component {
    static template = "account_online_payment.RefreshButton";
    static props = ["name", "id", "record", "readonly"];

    setup() {
        this.state = useState({
            isFetching: false,
        });
        this.orm = useService("orm");
    }

    get paymentOnlineStatus() {
        return this.props.record.data.payment_online_status;
    }

    async onClickFetchStatus() {
        this.state.isFetching = true;

        await this.orm.call("account.batch.payment", "check_online_payment_status", [
            this.props.record.data.id,
        ]);

        this.props.record.model.load();
        this.state.isFetching = false;
    }
}

export const refreshButtonComp = {
    component: RefreshButton,
};

registry.category("fields").add("account_online_payment_refresh_button", refreshButtonComp);
