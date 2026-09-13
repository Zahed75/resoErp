import { useSubEnv } from "@odoo/owl";
import { serializeDate } from "@web/core/l10n/dates";
import { SearchModel } from "@web/search/search_model";

const { DateTime } = luxon;


export class AccrualListSearchModel extends SearchModel {
    setup(services) {
        super.setup(services);
        this.accrualContext = {};
        useSubEnv({ accrualContext: this.accrualContext });
    }

    exportState() {
        return { ...super.exportState(), accrualContext: { ...this.accrualContext } };
    }

    _importState(state) {
        super._importState(state);
        Object.assign(this.accrualContext, state.accrualContext || {});
    }

    async load(config) {
        await super.load(config);
        this.accrualContext.accrual_entry_date ||= serializeDate(DateTime.now());
    }

    _getContext() {
        return Object.assign(super._getContext(), this.accrualContext);
    }
}
