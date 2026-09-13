import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const addSettleLine = (store, order) =>
    store.addLineToOrder(
        { product_tmpl_id: order.config.settle_invoice_product_id, qty: 1 },
        order
    );

const addSaleLine = (store, order) =>
    store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );

describe("pos_order.js", () => {
    test("setToInvoice on a sale", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await addSaleLine(store, order);

        order.setToInvoice(true);
        expect(order.isToInvoice()).toBe(true);
    });

    test("setToInvoice on a settlement", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await addSettleLine(store, order);
        expect(order.lines.at(-1).isAnySettleLine()).toBe(true);

        // settling pays an existing document: there is no sale to invoice
        order.setToInvoice(true);
        expect(order.isToInvoice()).toBe(false);
    });

    test("setToInvoice on a sale that also settles", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await addSaleLine(store, order);
        await addSettleLine(store, order);

        // the sale still has to be invoiced
        order.setToInvoice(true);
        expect(order.isToInvoice()).toBe(true);
    });

    test("setToInvoice on a deposit", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order.is_settling_account = true;

        order.setToInvoice(true);
        expect(order.isToInvoice()).toBe(false);
    });
});
