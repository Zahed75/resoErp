import { test, expect } from "@odoo/hoot";
import { mockService, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

definePosModels();

test("refunding an order for Consumidor Final shows an error dialog instead of crashing", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(store, {
        isEcuadorianCompany() {
            return true;
        },
    });

    const finalConsumer = store.models["res.partner"].get(3);
    store.config._final_consumer_id = finalConsumer.id;

    const order = await getFilledOrder(store, {}, false, true);
    order.setPartner(finalConsumer);

    const screen = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    let dialogProps;
    mockService("dialog", {
        add(component, props) {
            expect(component).toBe(AlertDialog);
            dialogProps = props;
        },
    });

    await screen.validateOrder();

    expect(dialogProps.title).toBe("Refund not possible");
    expect(dialogProps.body).toBe("You cannot refund orders for Consumidor Final.");
});
