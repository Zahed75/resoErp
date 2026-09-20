/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { WebClient } from "@web/webclient/webclient";

const PMS_ROOT_XMLIDS = [
    "rcloud_base.menu_rcloud_root",   // Resort Cloud product
    "reso_pms.menu_reso_pms_root",    // legacy Reso deployment
];

function redirectToPmsDashboard(menus) {
    const app = menus.getApps().find((a) =>
        PMS_ROOT_XMLIDS.includes(a.xmlid)
        || /resort pms|reso pms/i.test(a.name || ''));
    /* Root apps carry the action of their first child (server-side
       load_web_menus), so selecting the root opens the dashboard. */
    if (app && app.actionID) {
        menus.selectMenu(app);
    }
}

/* The home_menu service only registers the "menu" action component when it
   STARTS, so it cannot be patched at module-load time. WebClient.setup runs
   once, after services are up — patch the action class there. */
patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        const HomeMenuAction = registry.category("actions").get("menu", null);
        if (HomeMenuAction && !HomeMenuAction.prototype._rcRedirectPatched) {
            HomeMenuAction.prototype._rcRedirectPatched = true;
            patch(HomeMenuAction.prototype, {
                async onMounted() {
                    await super.onMounted(...arguments);
                    /* Full-page home has no action behind it; the
                       waffle-toggled overlay always keeps breadcrumbs. */
                    if (this.env.config.breadcrumbs.length === 0) {
                        redirectToPmsDashboard(this.menus);
                    }
                },
            });
        }
    },
});

/* Fallback: same redirect from the HomeMenu component itself, for any
   edge where the action wrapper is bypassed. */
patch(HomeMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcRedirected = false;
        const tryRedirect = () => {
            if (this._rcRedirected || !this.homeMenuService.hasHomeMenu
                || this.homeMenuService.hasBackgroundAction) {
                return;
            }
            this._rcRedirected = true;
            redirectToPmsDashboard(this.menus);
        };
        const id = setInterval(tryRedirect, 300);
        setTimeout(() => clearInterval(id), 5000);
    },
});
