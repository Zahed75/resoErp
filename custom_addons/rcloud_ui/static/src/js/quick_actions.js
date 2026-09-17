/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/* Top-bar quick actions (UIdesign 02 nav shell): New Reservation,
   Check In, Check Out — always visible, never inside a "+ New" menu. */
export class RcloudQuickActions extends Component {
    static template = "rcloud_ui.QuickActions";
    static props = {};

    setup() {
        this.action = useService("action");
    }

    newReservation() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "rcloud.reservation",
            views: [[false, "form"]],
        });
    }

    openArrivals() {
        this.action.doAction("rcloud_pms.action_arrivals");
    }

    openDepartures() {
        this.action.doAction("rcloud_pms.action_inhouse");
    }
}

registry.category("systray").add(
    "rcloud_ui.quick_actions", { Component: RcloudQuickActions }, { sequence: 10 });
