import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    // @Override
    setToInvoice(to_invoice) {
        if (
            (this.is_settling_account && this.lines.length === 0) ||
            (this.lines.length > 0 && this.lines.every((line) => line.isAnySettleLine()))
        ) {
            super.setToInvoice(false);
        } else {
            super.setToInvoice(to_invoice);
        }
    },
});
