/** @odoo-module **/

import { Component, useState, onWillStart, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

export class RcloudDashboard extends Component {
    static template = "rcloud_ui.Dashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.root = useRef("root");
        this.state = useState({
            loading: true,
            properties: [],
            propertyId: localStorage.getItem("rcloud.propertyId") || "all",
            stats: null,
            tab: "arrivals",
            dark: localStorage.getItem("rcloud.theme") === "dark",
        });
        onWillStart(async () => {
            this._applyTheme();
            await this.loadProperties();
            await this.loadStats();
        });
    }

    _applyTheme() {
        if (this.state.dark) {
            document.documentElement.setAttribute("data-rc-theme", "dark");
        } else {
            document.documentElement.removeAttribute("data-rc-theme");
        }
    }

    toggleTheme() {
        this.state.dark = !this.state.dark;
        localStorage.setItem("rcloud.theme", this.state.dark ? "dark" : "light");
        this._applyTheme();
    }

    async loadProperties() {
        this.state.properties = await this.orm.searchRead(
            "rcloud.property", [["active", "=", true]], ["id", "name"]);
    }

    async loadStats() {
        this.state.loading = true;
        const pid = this.state.propertyId !== "all"
            ? parseInt(this.state.propertyId) : null;
        this.state.stats = await this.orm.call(
            "rcloud.reservation", "get_dashboard_stats", [pid]);
        this.state.loading = false;
    }

    async onPropertyChange(ev) {
        this.state.propertyId = ev.target.value;
        localStorage.setItem("rcloud.propertyId", this.state.propertyId);
        await this.loadStats();
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    async checkIn(id, ev) {
        ev.stopPropagation();
        await this.orm.call("rcloud.reservation", "action_check_in", [[id]]);
        await this.loadStats();
    }

    async checkOut(id, ev) {
        ev.stopPropagation();
        await this.orm.call("rcloud.reservation", "action_check_out", [[id]]);
        await this.loadStats();
    }

    openRoom(room) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "rcloud.room",
            res_id: room.id,
            views: [[false, "form"]],
        });
    }

    openReservation(res) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "rcloud.reservation",
            res_id: res.id,
            views: [[false, "form"]],
        });
    }

    fmtMoney(v) {
        return (v || 0).toLocaleString("en-US",
            { maximumFractionDigits: 0 });
    }

    revenueDelta() {
        const k = this.state.stats.kpis;
        if (!k.revenue_prev_30d) { return null; }
        return Math.round(
            (k.revenue_30d - k.revenue_prev_30d) / k.revenue_prev_30d * 100);
    }

    trendPoints(key) {
        const trend = this.state.stats.trend || [];
        if (trend.length < 2) { return ""; }
        const values = trend.map(t => t[key] || 0);
        const max = Math.max(...values, 1);
        const step = 100 / (trend.length - 1);
        return values.map((v, i) =>
            `${(i * step).toFixed(1)},${(100 - (v / max) * 90 - 5).toFixed(1)}`
        ).join(" ");
    }

    maxSource() {
        const src = this.state.stats.revenue_by_source || [];
        return Math.max(...src.map(s => s.amount), 1);
    }

    hkPercent() {
        const k = this.state.stats.kpis;
        if (!k.rooms_total) { return 0; }
        return Math.round(k.clean / k.rooms_total * 100);
    }
}

registry.category("actions").add("rcloud_pms_dashboard", RcloudDashboard);
