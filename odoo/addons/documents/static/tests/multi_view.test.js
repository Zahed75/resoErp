import { animationFrame, describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { inputFiles } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineActions,
    defineModels,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import {
    DocumentsModels,
    getDocumentsTestServerModelsData,
} from "@documents/../tests/helpers/data";
import { makeDocumentsMockEnv } from "@documents/../tests/helpers/model";
import { embeddedActionsServerData } from "@documents/../tests/helpers/test_server_data";
import { basicDocumentsKanbanArch } from "@documents/../tests/helpers/views/kanban";
import { basicDocumentsListArch } from "@documents/../tests/helpers/views/list";
import { getEnrichedSearchArch } from "@documents/../tests/helpers/views/search";
import { EventBus } from "@odoo/owl";

defineModels(DocumentsModels);
defineActions([
    {
        id: 1,
        name: "Documents",
        res_model: "documents.document",
        views: [
            [false, "kanban"],
            [false, "list"],
        ],
    },
]);

describe.current.tags("desktop");

test("Keep showing actions on view switch", async function () {
    DocumentsModels.DocumentsDocument._views = {
        kanban: basicDocumentsKanbanArch,
        list: basicDocumentsListArch,
        [["search", false]]: getEnrichedSearchArch(),
    };
    await makeDocumentsMockEnv({ serverData: embeddedActionsServerData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    expect(`.o_kanban_view .o_content.o_component_with_search_panel`).toHaveCount(1);
    await contains(`.o_kanban_record:contains('Request 1')`).click();
    await waitFor(".o_control_panel_actions:contains('Action 1')");

    await getService("action").switchView("list");
    await waitFor(".o_data_row:contains('Request 1')");
    await waitFor(".o_control_panel_actions:contains('Action 1')");

    await getService("action").switchView("kanban");
    await waitFor(".o_kanban_record:contains('Request 1')");
    await waitFor(".o_control_panel_actions:contains('Action 1')");
});

test("Document Upload One File", async function () {
    onRpc("/documents/touch/<access_token>", () => ({}));
    onRpc("ir.model", "display_name_for", ({ args }) =>
        args[0].map((model) => ({ model, display_name: model }))
    );

    DocumentsModels.DocumentsDocument._views = {
        kanban: basicDocumentsKanbanArch,
        list: basicDocumentsListArch,
        [["search", false]]: getEnrichedSearchArch(),
    };

    localStorage.setItem("documentsChatterVisible", "true");

    const bus = new EventBus();
    let uploadResponse = "[102]";
    mockService("file_upload", {
        bus,
        upload: async (route) => {
            if (route === "/documents/upload/") {
                expect.step("upload_done");
                bus.trigger("FILE_UPLOAD_LOADED", {
                    upload: {
                        data: new FormData(),
                        xhr: { status: 200, response: uploadResponse },
                    },
                });
            }
        },
    });

    const serverData = getDocumentsTestServerModelsData([
        {
            folder_id: 1,
            id: 101,
            name: "File 1",
            access_token: "accessToken",
            type: "binary",
        },
        {
            folder_id: 1,
            id: 102,
            name: "File 2",
            access_token: "accessToken",
            type: "binary",
        },
    ]);

    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await animationFrame();
    const file = new File(["hello world"], "text.txt", { type: "text/plain" });
    await inputFiles(".o_control_panel_main_buttons .o_input_file", [file]);
    await animationFrame();
    expect.verifySteps(["upload_done"]);
    await expect(".o_documents_details_panel").toBeVisible();
    await expect(".o_documents_details_panel_name input").toHaveValue("File 2");
    await expect(".o_selection_box b:contains('1')").toHaveCount(1); // 1 selected
    await expect(".o_record_selected").toHaveCount(1);
    await expect(".o_record_selected span:contains('File 2')").toHaveCount(1);
    await animationFrame();
    await expect(".o_control_panel_actions button:contains('Share')").toHaveCount(1); // action visible

    // switch to list view
    await getService("action").switchView("list");
    await waitFor(".o_data_row:contains('File 2')");
    await waitFor(".o_control_panel_actions:contains('Share')");
    await expect(".o_control_panel_actions button:contains('Share')").toHaveCount(1); // action still visible

    await getService("action").switchView("kanban");
    await waitFor(".o_kanban_record:contains('File 1')");
    await waitFor(".o_control_panel_actions:contains('Share')");
    await expect(".o_control_panel_actions button:contains('Share')").toHaveCount(1); // action still visible

    // now upload 2 files
    // the share action is not visible, we view the first documents in the detail panel
    // but both are selected
    uploadResponse = "[101, 102]";
    await inputFiles(".o_control_panel_main_buttons .o_input_file", [file, file]);
    await animationFrame();
    expect.verifySteps(["upload_done"]);
    await expect(".o_documents_details_panel_name input").toHaveValue("File 2");
    await expect(".o_selection_box b:contains('2')").toHaveCount(1); // 2 selected
    await expect(".o_record_selected").toHaveCount(2);
    await expect(".o_record_selected span:contains('File 1')").toHaveCount(1);
    await expect(".o_record_selected span:contains('File 2')").toHaveCount(1);
});
