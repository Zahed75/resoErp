/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";

const PMS_ROOT_XMLIDS = [
    "rcloud_base.menu_rcloud_root",   // Resort Cloud product
    "reso_pms.menu_reso_pms_root",    // legacy Reso deployment
];

/* Full-page home (breadcrumbs empty) must land on the Reso PMS dashboard,
   but the waffle-toggled HomeMenu overlay (background action open) keeps
   working as the app switcher. The home_menu service exposes exactly this
   distinction: HomeMenuAction.onMounted sets
       state.hasBackgroundAction = breadcrumbs.length > 0
   (home_menu_service.js), i.e. false iff the home menu IS the main screen.
   The state is written by the PARENT (HomeMenuAction) onMounted, which OWL
   runs after the child's, so the check is deferred one tick. */
patch(HomeMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this._rcRedirected = false;
        onMounted(() => {
            setTimeout(() => {
                if (this._rcRedirected || !this.homeMenuService.hasHomeMenu
                    || this.homeMenuService.hasBackgroundAction) {
                    return;
                }
                this._rcRedirected = true;
                const app = this.menus.getApps().find((a) =>
                    PMS_ROOT_XMLIDS.includes(a.xmlid)
                    || /resort pms|reso pms/i.test(a.name || ''));
                /* Root apps carry the action of their first child (server-side
                   load_web_menus), so selecting the root opens the dashboard. */
                if (app && app.actionID) {
                    this.menus.selectMenu(app);
                }
            }, 0);
        });
    },
});
