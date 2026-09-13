import { PosConfig } from "@point_of_sale/app/models/pos_config";
import { patch } from "@web/core/utils/patch";

patch(PosConfig.prototype, {
    get posSwVersion() {
        return odoo.info?.server_version || this._server_version.server_version;
    },
    /** Track line state changes for blackbox corrections (skip in self-order mode). */
    get trackBlackboxCorrections() {
        return Boolean(this.l10n_be_blackbox_be_id) && !this._self_order_pos;
    },
});
