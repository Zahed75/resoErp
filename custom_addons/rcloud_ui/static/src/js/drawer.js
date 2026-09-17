/** @odoo-module **/

import { Component, useState, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { EnterpriseNavBar } from "@web_enterprise/webclient/navbar/navbar";

/* Material Design Icons (Apache-2.0, pictogrammers.github.io/mdi) */
const MDI = {
    home: "M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z",
    bed: "M19,7H11V14H3V5H1V20H3V17H21V20H23V11A4,4 0 0,0 19,7M7,13A2,2 0 0,0 9,11A2,2 0 0,0 7,9A2,2 0 0,0 5,11A2,2 0 0,0 7,13Z",
    forum: "M12,3C6.5,3 2,6.58 2,11C2,13.13 3.05,15.07 4.75,16.5C4.7,18.38 3.5,20 3.5,20H12A9,9 0 0,0 21,11C21,6.58 16.5,3 12,3M7,12A1.5,1.5 0 0,1 5.5,10.5A1.5,1.5 0 0,1 7,9A1.5,1.5 0 0,1 8.5,10.5A1.5,1.5 0 0,1 7,12M12,12A1.5,1.5 0 0,1 10.5,10.5A1.5,1.5 0 0,1 12,9A1.5,1.5 0 0,1 13.5,10.5A1.5,1.5 0 0,1 12,12M17,12A1.5,1.5 0 0,1 15.5,10.5A1.5,1.5 0 0,1 17,9A1.5,1.5 0 0,1 18.5,10.5A1.5,1.5 0 0,1 17,12Z",
    calendar: "M19,19H5V8H19M16,1V3H8V1H6V3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3H18V1Z",
    account: "M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.4,14 20,15.79 20,18V20H4V18C4,15.79 7.6,14 12,14Z",
    chart: "M22,21H2V3H4V19H6V10H10V19H12V6H16V19H18V14H22V21Z",
    cash: "M3,6H21V18H3V6M12,9.5A2.5,2.5 0 0,1 14.5,12A2.5,2.5 0 0,1 12,14.5A2.5,2.5 0 0,1 9.5,12A2.5,2.5 0 0,1 12,9.5M7,8A1,1 0 0,1 6,9A1,1 0 0,1 7,10A1,1 0 0,1 8,9A1,1 0 0,1 7,8M17,14A1,1 0 0,1 16,15A1,1 0 0,1 17,16A1,1 0 0,1 18,15A1,1 0 0,1 17,14Z",
    cog: "M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.4,13C19.5,12.7 19.5,12.4 19.5,12C19.5,11.6 19.5,11.3 19.4,11L21.5,9.4L19.5,6.6L17,7.5C16.4,7 15.7,6.6 15,6.3L14.7,3.8H11.3L11,6.3C10.3,6.6 9.6,7 9,7.5L6.5,6.6L4.5,9.4L6.6,11C6.5,11.3 6.5,11.6 6.5,12C6.5,12.4 6.5,12.7 6.6,13L4.5,14.6L6.5,17.4L9,16.5C9.6,17 10.3,17.4 11,17.7L11.3,20.2H14.7L15,17.7C15.7,17.4 16.4,17 17,16.5L19.5,17.4L21.5,14.6L19.4,13Z",
    grid: "M3,11H11V3H3M3,21H11V13H3M13,21H21V13H13M13,3V11H21V3",
    cart: "M17,18C15.89,18 15,18.89 15,20A2,2 0 0,0 17,22A2,2 0 0,0 19,20C19,18.89 18.1,18 17,18M1,2V4H3L6.6,11.59L5.24,14.04C5.09,14.32 5,14.65 5,15A2,2 0 0,0 7,17H19V15H7.42A0.25,0.25 0 0,1 7.17,14.75C7.17,14.7 7.18,14.66 7.2,14.63L8.1,13H15.55C16.3,13 16.96,12.59 17.3,11.97L20.88,5.5C20.95,5.34 21,5.17 21,5A1,1 0 0,0 20,4H5.21L4.27,2M7,18C5.89,18 5,18.89 5,20A2,2 0 0,0 7,22A2,2 0 0,0 9,20C9,18.89 8.1,18 7,18Z",
    link: "M3.9,12A3.1,3.1 0 0,1 7,8.9C7.28,8.9 7.56,8.94 7.82,9L7.9,9L8.83,7.8C8.16,7.31 7.13,7 6,7C3.24,7 1,9.24 1,12C1,14.76 3.24,17 6,17C7.13,17 8.16,16.69 8.83,16.2L7.9,15C7.56,15.06 7.28,15.1 7,15.1A3.1,3.1 0 0,1 3.9,12M8,9.8L12.67,13.44L13.79,12.31L9.14,8.68C8.75,9.06 8.4,9.41 8,9.8M16,7C14.87,7 13.84,7.31 13.17,7.8L14.1,9C14.44,8.94 14.72,8.9 15,8.9A3.1,3.1 0 0,1 18.1,12A3.1,3.1 0 0,1 15,15.1C14.72,15.1 14.44,15.06 14.1,15L13.17,16.2C13.84,16.69 14.87,17 16,17C18.76,17 21,14.76 21,12C21,9.24 18.76,7 16,7M16.33,9.82L11.67,13.46L10.55,12.33L15.22,8.68C15.6,9.07 15.95,9.43 16.33,9.82Z",
    flask: "M6,22A3,3 0 0,1 3,19C3,18.4 3.18,17.84 3.5,17.37L9,7.81V6A1,1 0 0,1 8,5V4A2,2 0 0,1 10,2H14A2,2 0 0,1 16,4V5A1,1 0 0,1 15,6V7.81L20.5,17.37C20.82,17.84 21,18.4 21,19A3,3 0 0,1 18,22H6Z",
    briefcase: "M14,6H10V4H14M20,6H16V4L14,2H10L8,4V6H4A2,2 0 0,0 2,8V19A2,2 0 0,0 4,21H20A2,2 0 0,0 22,19V8A2,2 0 0,0 20,6Z",
    folder: "M10,4H4A2,2 0 0,0 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8A2,2 0 0,0 20,6H12L10,4Z",
    receipt: "M3,22L4.5,20.5L6,22L7.5,20.5L9,22L10.5,20.5L12,22L13.5,20.5L15,22L16.5,20.5L18,22L19.5,20.5L21,22V2L19.5,3.5L18,2L16.5,3.5L15,2L13.5,3.5L12,2L10.5,3.5L9,2L7.5,3.5L6,2L4.5,3.5L3,2M18,9H6V7H18M18,13H6V11H18M18,17H6V15H18V17Z",
    chartLine: "M16,11.78L20.24,4.45L21.97,5.45L16.74,14.5L10.23,10.75L5.46,19H22V21H2V3H4V17.54L9.5,8L16,11.78Z",
};

const ICON_BY_NAME = [
    [/^reso pms$|^resort pms$/i, MDI.bed],
    [/^discuss$/i, MDI.forum],
    [/^reso ownership$|^ownership$/i, MDI.chartLine],
    [/^calendar$/i, MDI.calendar],
    [/^contacts?$/i, MDI.account],
    [/^crm$/i, MDI.chart],
    [/^sales?$/i, MDI.cart],
    [/^dashboards?$/i, MDI.chartLine],
    [/^point of sale|pos$/i, MDI.receipt],
    [/^accounting|invoicing$/i, MDI.cash],
    [/^website$/i, MDI.link],
    [/^purchase|inventory$/i, MDI.briefcase],
    [/^barcode$/i, MDI.grid],
    [/^employees|hr$/i, MDI.account],
    [/^expenses$/i, MDI.receipt],
    [/^apps$/i, MDI.grid],
    [/^settings$/i, MDI.cog],
    [/^tests?$/i, MDI.flask],
    [/^link tracker$/i, MDI.link],
    [/^documents?$/i, MDI.folder],
];

const GROUPS = [
    { label: "Operations", match: /^reso pms$|^resort pms$|point of sale|kitchen|housekeep/i },
    { label: "Sales", match: /crm|sales|calendar|contacts/i },
    { label: "Finance", match: /accounting|invoicing|expenses/i },
    { label: "People", match: /employees/i },
    { label: "Settings", match: /settings|^apps$/i },
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

    iconFor(name) {
        name = name || '';
        for (const [re, path] of ICON_BY_NAME) {
            if (re.test(name)) { return path; }
        }
        return MDI.grid;
    }

    get apps() {
        // Keep the RAW menu objects: the menu service relies on their
        // identity/proxy internals — plain copies break selectMenu.
        let roots = this.menu.getApps() || [];
        if (!roots.length) {
            // Menus not loaded yet (fresh session) — trigger a reload.
            this.menu.reload();
            roots = this.menu.getApps() || [];
        }
        if (!this.state.filter) { return roots; }
        const f = this.state.filter.toLowerCase();
        return roots.filter((a) => (a.name || '').toLowerCase().includes(f));
    }

    get grouped() {
        const apps = this.apps;
        const groups = GROUPS.map((g) => ({
            label: g.label,
            apps: apps.filter((a) => g.match.test(a.name)),
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

    async openApp(app) {
        this.state.open = false;
        // Odoo 19 menu service API: selectMenu(menu object). The raw app
        // object must be passed — copies break the service internals.
        await this.menu.selectMenu(app);
    }

    onSearch(ev) {
        this.state.filter = ev.target.value;
    }

    openAppsManager() {
        this.state.open = false;
        // Odoo's module kanban: admins can install/update apps here;
        // access rights keep it admin-only automatically.
        this.action.doAction("base.open_module_tree");
    }

    openSettings() {
        this.state.open = false;
        this.action.doAction("base_setup.action_general_configuration");
    }
}

/* Mounted inside the navbar at the far LEFT (nav shell spec) — not systray. */
EnterpriseNavBar.components = {
    ...EnterpriseNavBar.components,
    RcloudDrawerToggle,
};
