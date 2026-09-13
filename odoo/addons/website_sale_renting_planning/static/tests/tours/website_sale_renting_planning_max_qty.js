import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add("website_sale_renting_planning_max_qty", {
    steps: () => [
        {
            content: "Select Product Renting Planning",
            trigger: ".oe_product_cart:first a:contains('Product Renting Planning')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Wait for the daterange picker to be initialized",
            trigger: ".o_daterange_picker[data-has-default-dates]",
        },
        {
            content: "Pick a valid start date",
            trigger: "input[name=renting_start_date]",
            run: "edit 03/12/2999 && press Tab",
        },
        {
            content: "Pick a valid end date",
            trigger: "input[name=renting_end_date]",
            run: "edit 03/15/2999 && press Tab",
        },
        {
            content: "Add one quantity",
            trigger: ".css_quantity a.js_add_cart_json i.oi-plus",
            run: "click",
        },
        {
            content: "One quantity should be added",
            trigger: "input[name=add_qty]:value('2')",
        },
        {
            content: "Try to add one quantity",
            trigger: ".css_quantity a.js_add_cart_json i.oi-plus",
            run: "click",
        },
        {
            content: "No quantity should be added",
            trigger: "input[name=add_qty]:value('2')",
        },
        {
            content: "Pick a valid end date",
            trigger: "input[name=renting_end_date]",
            run: "edit 03/18/2999 && press Tab",
        },
        {
            content: "Check that css_not_available has been added to the product form",
            trigger: "form.css_not_available",
        },
        {
            content: "Quantity should have been reset",
            trigger: "input[name=add_qty]:value('1')",
        },
        {
            content: "Try to add one quantity",
            trigger: ".css_quantity a.js_add_cart_json i.oi-plus",
            run: "click",
        },
        {
            content: "No quantity should be added",
            trigger: "input[name=add_qty]:value('1')",
        },
        {
            content: "Pick a valid end date",
            trigger: "input[name=renting_end_date]",
            run: "edit 03/15/2999 && press Tab",
        },
        {
            content: "Add product to cart",
            trigger: "#product_detail form #add_to_cart",
            run: "click",
        },
        tourUtils.goToCart(),
        {
            content: "Add one quantity",
            trigger: "div[name='website_sale_cart_line_quantity'] a.btn i.oi-plus",
            run: "click",
        },
        {
            content: "One quantity should be added",
            trigger: "div[name='website_sale_cart_line_quantity'] input.quantity:value('2')",
        },
        {
            content: "Try to add one quantity",
            trigger: "div[name='website_sale_cart_line_quantity'] a.btn i.oi-plus",
            run: "click",
        },
        {
            content: "No quantity should be added",
            trigger: "div[name='website_sale_cart_line_quantity'] input.quantity:value('2')",
        },
    ],
});
