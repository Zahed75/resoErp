/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";

const PMS_ROOT_XMLIDS = [
    "rcloud_base.menu_rcloud_root",   // Resort Cloud product
    "reso_pms.menu_reso_pms_root",    // legacy Reso deployment
];

function pmsApp(menus) {
    return menus.getApps().find((a) =>
        PMS_ROOT_XMLIDS.includes(a.xmlid)
        || /resort pms|reso pms/i.test(a.name || ''));
}

/* Default screen is the PMS dashboard: whenever the browser address is the
   bare home route (/odoo, no action behind it) we select the Reso PMS app,
   whose root carries the dashboard action (server-side load_web_menus).

   This is URL-driven rather than mount-driven on purpose: going Back from a
   scoped app route (e.g. /odoo/contacts) restores the home controller from
   the action cache without remounting it, so mount hooks never fire there.
   The waffle app drawer does not touch the address bar, and the home overlay
   never sets a bare /odoo URL, so this never hijacks app switching. */
patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        const menus = useService("menu");
        let coolDownUntil = 0;
        setInterval(() => {
            if (location.pathname !== "/odoo") {
                coolDownUntil = 0;
                return;
            }
            const now = Date.now();
            if (now < coolDownUntil) {
                return;
            }
            const app = pmsApp(menus);
            if (!app || !app.actionID) {
                return;
            }
            coolDownUntil = now + 3000;
            setTimeout(() => {
                /* Re-check both conditions at fire time: selectMenu resolves
                   asynchronously and a late push would otherwise hijack a
                   screen the user opened in between. When a real app is
                   current (dashboard, documents, any action), never redirect. */
                if (location.pathname === "/odoo" && !menus.getCurrentApp()) {
                    menus.selectMenu(app);
                }
            }, 400);
        }, 500);
    },
});
