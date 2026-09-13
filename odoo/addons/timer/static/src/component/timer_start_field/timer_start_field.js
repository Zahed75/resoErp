import { Component, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useTimer } from "../../hooks/use_timer";

export class TimerStartField extends Component {
    static props = {
        ...standardFieldProps,
        valueFieldName: { type: String, optional: true },
    };
    static template = "timer.TimerStartField";

    setup() {
        super.setup(...arguments);
        this.timerReactive = useState(useTimer());

        useRecordObserver(this.onRecordChange.bind(this));
        useEffect(
            () => {
                const timerStart = this.props.record.data[this.props.name];
                if (!timerStart || this.props.record.data.timer_pause) {
                    return;
                }
                const interval = setInterval(() => {
                    this.timerReactive.updateTimer(timerStart);
                    this.timerReactive.formatTime();
                }, 1000);
                return () => clearInterval(interval);
            },
            () => {
                // Compare values, not DateTime object references.
                const timerStart = this.props.record.data[this.props.name];
                const timerPause = this.props.record.data.timer_pause;
                return [timerStart?.valueOf(), timerPause?.valueOf()];
            }
        );
    }

    get value() {
        return this.props.record.data[this.props.valueFieldName] || 0;
    }

    onRecordChange(record) {
        const timerStart = record.data[this.props.name];
        if (!timerStart) {
            this.timerReactive.resetTimer();
            return;
        }
        const timerPause = record.data.timer_pause;
        const currentTime = timerPause ? timerPause : this.timerReactive.getCurrentTime();
        this.timerReactive.setTimer(this.value, timerStart, currentTime);
        this.timerReactive.formatTime();
    }
}

export const timerStartField = {
    component: TimerStartField,
    fieldDependencies: ({ type, attrs, options }) => {
        const deps = [{ name: "timer_pause", type: "datetime" }];
        if (options["unit_amount_field"]) {
            deps.push({ name: options["unit_amount_field"], type, ...attrs });
        }
        return deps;
    },
    extractProps: ({ options }, dynamicInfo) => ({
        valueFieldName: options["unit_amount_field"],
    }),
};

registry.category("fields").add("timer_start_field", timerStartField);
