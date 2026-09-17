/** @odoo-module **/

import { Component, useState, useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const GROUPS = [
    { label: "Operations", apps: ["Resort PMS"] },
    { label: "Sales", apps: ["CRM", "Sales", "Calendar", "Contacts"] },
    { label: "Finance", apps: ["Accounting", "Invoicing", "Expenses"] },
    { label: "People", apps: ["Employees"] },
    { label: "Settings", apps: ["Settings", "Apps"] },
];

export class RcloudDrawerToggle extends Component {
    static template = "rcloud_ui.Drawer";
    static props = {};

    setup() {
        this.menu = useService("menu");
        this.action = useService("action");
        this.state = useState({ open: false, filter: "" });
        useExternalListener(document, "keydown", (ev) => {
            if (ev.key === "Escape") { this.state.open = false; }
        });
    }

    get apps() {
        const roots = (this.menu.getApps() || []).map((a) => ({
            name: a.name,
            xmlid: a.xmlid,
            id: a.menuID,
        }));
        if (!this.state.filter) { return roots; }
        const f = this.state.filter.toLowerCase();
        return roots.filter((a) => a.name.toLowerCase().includes(f));
    }

    get grouped() {
        const apps = this.apps;
        const groups = GROUPS.map((g) => ({
            label: g.label,
            apps: apps.filter((a) => g.apps.includes(a.name)),
        })).filter((g) => g.apps.length);
        const used = new Set(groups.flatMap((g) => g.apps.map((a) => a.name)));
        const rest = apps.filter((a) => !used.has(a.name));
        if (rest.length) {
            groups.push({ label: "More", apps: rest });
        }
        return groups;
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    close() {
        this.state.open = false;
    }

    openApp(app) {
        this.state.open = false;
        this.menu.selectApp(app.id);
    }

    onSearch(ev) {
        this.state.filter = ev.target.value;
    }
}

registry.category("systray").add(
    "rcloud_ui.drawer_toggle", { Component: RcloudDrawerToggle }, { sequence: 5 });
