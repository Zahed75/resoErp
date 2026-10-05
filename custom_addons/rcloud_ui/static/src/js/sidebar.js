/** @odoo-module **/

import { Component, useState, useEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

const PMS_ROOT_XMLIDS = [
    "rcloud_base.menu_rcloud_root",   // Resort Cloud product
    "reso_pms.menu_reso_pms_root",    // legacy Reso deployment
];

export class RcloudSidebar extends Component {
    static template = "rcloud_ui.Sidebar";
    static props = {};

    setup() {
        this.menu = useService("menu");
        this.action = useService("action");
        this.env = useEnv();
        this.state = useState({
            collapsed: localStorage.getItem("rcloud.sidebar.collapsed") === "1",
            tick: 0,
        });
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => { this.state.tick++; });
    }

    get pmsRoot() {
        const roots = this.menu.getApps() || [];
        return roots.find((a) => PMS_ROOT_XMLIDS.includes(a.xmlid))
            || roots.find((a) => /resort pms|reso pms/i.test(a.name || ''));
    }

    get isPms() {
        void this.state.tick;
        const app = this.menu.getCurrentApp();
        /* Landing via the per-user home action leaves no current app —
           treat that as PMS context (the product's home IS the PMS). */
        if (!app) { return !!this.pmsRoot; }
        return PMS_ROOT_XMLIDS.includes(app.xmlid)
            || /resort pms|reso pms/i.test(app.name || '');
    }

    get activeMenuId() {
        return parseInt(localStorage.getItem("rcloud.sidebar.active") || "0");
    }

    get groups() {
        void this.state.tick;
        if (!this.isPms) { return []; }
        /* Always resolve the PMS root from the app list: the sidebar must
           stay populated even when the current app is unset (home action,
           direct URL) or the selection came from a menu copy. */
        const app = this.menu.getCurrentApp();
        const currentIsPms = app && (PMS_ROOT_XMLIDS.includes(app.xmlid)
            || /resort pms|reso pms/i.test(app.name || ''));
        const root = currentIsPms ? app : this.pmsRoot;
        if (!root) { return []; }
        const tree = this.menu.getMenuAsTree(root.id);
        return (tree.childrenTree || []).map((group) => ({
            id: group.id,
            label: group.name,
            items: (group.childrenTree || []).map((m) => ({
                id: m.id, name: m.name, actionID: m.actionID,
                active: m.id === this.activeMenuId,
            })),
        })).filter((g) => g.items.length);
    }

    toggle() {
        this.state.collapsed = !this.state.collapsed;
        localStorage.setItem("rcloud.sidebar.collapsed", this.state.collapsed ? "1" : "0");
    }

    async openMenu(item) {
        localStorage.setItem("rcloud.sidebar.active", String(item.id));
        /* Pass the RAW menu object — plain copies miss menu.appID, and
           selectMenu's setCurrentMenu would then clear the current app,
           emptying this sidebar (and the navbar sections). */
        const full = this.menu.getMenu(item.id);
        await this.menu.selectMenu(full);
        this.state.tick++;
    }
}

WebClient.components = { ...WebClient.components, RcloudSidebar };
/* Enterprise spreads WebClient.components at class-definition time, so it
   must be patched separately or the sidebar is undefined there. */
if (WebClientEnterprise) {
    WebClientEnterprise.components = {
        ...WebClientEnterprise.components, RcloudSidebar,
    };
}
