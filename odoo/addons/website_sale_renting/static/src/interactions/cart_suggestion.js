import { deserializeDateTime, serializeDateTime } from '@web/core/l10n/dates';
import { patch } from '@web/core/utils/patch';
import { CartSuggestion } from '@website_sale/interactions/cart_suggestion';

patch(CartSuggestion.prototype, {
    /**
     * @param {Event} ev
     */
    addSuggestedProduct(ev) {
        const dataset = ev.currentTarget.dataset;

        this.services["cart"].add(
            {
                productTemplateId: parseInt(dataset.productTemplateId),
                productId: parseInt(dataset.productId),
                isCombo: dataset.productType === 'combo',
                // The dates are rendered as raw str(datetime) into the data
                // attributes, which keeps the .999999 microseconds of an
                // end-of-day return date. Round-trip them to the standard
                // server format so the controller's to_datetime() can parse it.
                start_date: dataset.rentalStartDate
                    && serializeDateTime(deserializeDateTime(dataset.rentalStartDate)),
                end_date: dataset.rentalReturnDate
                    && serializeDateTime(deserializeDateTime(dataset.rentalReturnDate)),
            },
            {
                isBuyNow: true,
                showQuantity: Boolean(dataset.showQuantity),
            }
        );
    },
});
