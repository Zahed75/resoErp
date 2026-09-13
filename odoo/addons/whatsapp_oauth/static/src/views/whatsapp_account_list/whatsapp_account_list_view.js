import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

import { WhatsappAccountListController } from "./whatsapp_account_list_view_controller";

const whatsappAccountListView = {
    ...listView,
    buttonTemplate: "whatsapp_oauth.WhatsappAccountListButtons",
    Controller: WhatsappAccountListController,
};

registry.category("views").add("whatsapp_oauth.whatsapp_account_list", whatsappAccountListView);
