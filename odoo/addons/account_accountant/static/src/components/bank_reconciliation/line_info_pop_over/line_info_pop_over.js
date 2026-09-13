import { Component } from "@odoo/owl";
import { formatMonetary } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";

export class BankRecLineInfoPopOver extends Component {
    static template = "account_accountant.BankRecLineInfoPopOver";
    static props = {
        lineData: { type: Object, optional: true },
        statementLineData: { type: Object, optional: true },
        exchangeMove: { type: Object, optional: true },
        isPartiallyReconciled: { type: Boolean, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.action = useService("action");
    }

    openExchangeMove() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: this.props.exchangeMove.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openReconciledMove() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: this.reconciledLineData.move_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    get reconciledMoveName() {
        return this.reconciledLineData.move_name;
    }

    get formattedReconciledMoveAmountCurrency() {
        return formatMonetary(this.reconciledLineData.amount_currency, {
            currencyId: this.reconciledLineData.currency_id.id,
        });
    }

    get reconciledLineData() {
        return this.props.lineData.first_reconciled_lines_id;
    }

    get formattedLineDataAmountCurrency() {
        return formatMonetary(this.props.lineData.amount_currency, {
            currencyId: this.props.lineData.currency_id.id,
        });
    }

    get exchangeDiffMoveName() {
        return this.props.exchangeMove.display_name;
    }

    get exchangeMoveBalance() {
        return this.props.exchangeMove.amount_total_signed;
    }

    get formattedExchangeMoveBalance() {
        return formatMonetary(this.exchangeMoveBalance, {
            currencyId: this.props.statementLineData.company_id.currency_id?.id,
        });
    }
}
