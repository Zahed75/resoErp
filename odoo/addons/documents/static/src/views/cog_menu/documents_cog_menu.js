import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { documentsCogMenuItemArchive } from "./documents_cog_menu_item_archive";
import { documentCogMenuPinAction } from "./documents_cog_menu_pin_actions";
import { documentsCogMenuItemDetails } from "./documents_cog_menu_item_details";
import { documentsCogMenuItemDownload } from "./documents_cog_menu_item_download";
import { documentsCogMenuItemShare } from "./documents_cog_menu_item_share";
import { documentsCogMenuItemRename } from "./documents_cog_menu_item_rename";
import { documentsCogMenuItemShortcut } from "./documents_cog_menu_item_shortcut";
import {
    documentsCogMenuItemStarAdd,
    documentsCogMenuItemStarRemove,
} from "./documents_cog_menu_item_star";
import { documentsCogMenuItemAutomations } from "./documents_cog_menu_item_automations";

const documentMenuItems = [
    documentsCogMenuItemDownload,
    documentsCogMenuItemRename,
    documentsCogMenuItemShare,
    documentsCogMenuItemShortcut,
    documentsCogMenuItemStarAdd,
    documentsCogMenuItemStarRemove,
    documentsCogMenuItemDetails,
    documentsCogMenuItemArchive,
    documentCogMenuPinAction,
    documentsCogMenuItemAutomations,
];

export class DocumentsCogMenu extends CogMenu {
    async _registryItems() {
        const documentItemsPromise = documentMenuItems.map(async (item) =>
            (await item.isDisplayed(this.env)) ? formatRegistryItem(item) : false
        );
        const [enabledItems, items] = await Promise.all([
            super._registryItems(),
            Promise.all(documentItemsPromise),
        ]);
        return enabledItems.concat(items.filter(Boolean));
    }
}

function formatRegistryItem(item) {
    return {
        Component: item.Component,
        groupNumber: item.groupNumber,
        key: item.Component.name,
    };
}
