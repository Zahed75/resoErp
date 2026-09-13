import { test, expect, describe } from "@odoo/hoot";
import { setupPosBlackboxEnv } from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

const SELF_ORDERING_USER_INSZ = "00000000097";

describe("sign_self_order", () => {
    test("signed with the self-ordering default user", async () => {
        const signSaleInputs = [];
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                signSaleInputs.push(body.variables.data);
            }
            return {};
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store, {}, true);
        store.config._self_ordering_default_user_insz = SELF_ORDERING_USER_INSZ;
        patchWithCleanup(store.data, { callRelated: async () => ({ "pos.order": [order] }) });

        await store.getSelfOrderToPrint(order.id);

        expect(signSaleInputs).toHaveLength(1);
        expect(signSaleInputs[0].employeeId).toBe(SELF_ORDERING_USER_INSZ);
    });

    test("signed with the cashier when there is no self-ordering default user", async () => {
        const signSaleInputs = [];
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                signSaleInputs.push(body.variables.data);
            }
            return {};
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store, {}, true);
        patchWithCleanup(store.data, { callRelated: async () => ({ "pos.order": [order] }) });

        await store.getSelfOrderToPrint(order.id);

        expect(signSaleInputs).toHaveLength(1);
        expect(signSaleInputs[0].employeeId).toBe(store.getCashier().l10n_be_insz_or_bis_number);
    });
});
