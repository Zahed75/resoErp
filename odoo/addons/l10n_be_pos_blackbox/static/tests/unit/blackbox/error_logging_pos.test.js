import { test, describe, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosBlackboxEnv,
    waitForUnawaitedCalls,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { onRpc, patchTranslations } from "@web/../tests/web_test_helpers";

definePosModels();

const fdmErrorResponse = () =>
    new Response(
        JSON.stringify({
            errors: [
                {
                    message: "The FDM is locked",
                    path: ["signWorkIn"],
                    extensions: { code: "FDM_LOCKED", category: "FDM" },
                },
            ],
        }),
        { headers: { "Content-Type": "application/json" } }
    );

describe("blackbox error logging", () => {
    test("an error returned by the FDM is reported to the backend", async () => {
        patchTranslations();
        const logged = [];
        onRpc("pos.session", "log_blackbox_error", ({ args }) => {
            logged.push(args[1]);
            return true;
        });
        const store = await setupPosBlackboxEnv(async () => fdmErrorResponse(), {
            setupCashier: false,
        });

        await store.blackbox.signWorkIn.sign(store.models, "1234567890");
        await waitForUnawaitedCalls(() => expect(logged.length).toBe(1));

        expect(logged[0].mutation).toBe("signWorkIn");
        expect(logged[0].error_type).toBe("fdm");
        expect(logged[0].error_code).toBe("FDM_LOCKED");
        expect(logged[0].error_category).toBe("FDM");
        expect(logged[0].request_data.employeeId).toBe("1234567890");
        expect(logged[0].error_data[0].extensions.code).toBe("FDM_LOCKED");
    });

    test("nothing is reported when the FDM answers correctly", async () => {
        patchTranslations();
        let logCalls = 0;
        onRpc("pos.session", "log_blackbox_error", () => {
            logCalls++;
            return true;
        });
        const store = await setupPosBlackboxEnv(undefined, { setupCashier: false });

        await store.blackbox.signWorkIn.sign(store.models, "1234567890");
        await waitForUnawaitedCalls(() => expect(logCalls).toBe(0));
    });
});
