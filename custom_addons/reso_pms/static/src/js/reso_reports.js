/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ResoAnalyticsDashboard extends Component {
    static template = "reso_pms.ResoReportsTemplate";

    setup() {
        this.state = useState({
            activeTab: "occupancy",
            loading: true,
            currency: "BDT",
            occupancyData: [],
            revenueOutlets: [],
            ownershipYields: [],
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    async loadReport() {
        this.state.loading = true;
        try {
            const res = await fetch("/api/v1/pms/reports/occupancy", {
                headers: { "Accept": "application/json" },
            });
            const payload = await res.json();
            if (payload.status !== "success") {
                throw new Error(payload.message || "Report request failed.");
            }
            const data = payload.data || {};
            this.state.currency = data.currency || "BDT";
            const labels = data.labels || [];
            const occupancy = data.occupancy_rates || [];
            const adr = data.adr_values || [];
            const revpar = data.revpar_values || [];

            this.state.occupancyData = labels.map((label, i) => ({
                month: label,
                occupancy: occupancy[i] ?? 0,
                adr: adr[i] ?? 0,
                revpar: revpar[i] ?? 0,
                status: (occupancy[i] ?? 0) >= 80 ? "High Season" : "Normal",
            }));
            this.state.revenueOutlets = (data.revenue_by_outlet || []).map(o => ({
                category: o.category,
                gross: this._fmt(o.gross),
                percent: `${o.percent}%`,
            }));
            this.state.ownershipYields = (data.ownership_yields || []).map(y => ({
                name: y.name,
                property: y.property,
                shares: y.shares,
                percent: y.percent,
                dividend: this._fmt(y.dividend),
                status: y.status,
            }));
        } catch (e) {
            console.error("Error loading analytics report:", e);
        } finally {
            this.state.loading = false;
        }
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    _fmt(value) {
        return (value ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
    }

    _downloadCsv(filename, headers, rows) {
        const escape = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
        const csv = [
            headers.map(escape).join(","),
            ...rows.map((r) => r.map(escape).join(",")),
        ].join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    exportReport(reportName) {
        if (reportName.startsWith("Occupancy")) {
            this._downloadCsv(
                "reso_occupancy_report.csv",
                ["Month", "Occupancy Rate (%)", "ADR", "RevPAR", "Performance Index"],
                this.state.occupancyData.map((r) => [r.month, r.occupancy, r.adr, r.revpar, r.status]),
            );
        } else if (reportName.startsWith("Revenue")) {
            this._downloadCsv(
                "reso_revenue_report.csv",
                ["Outlet / Category", "Gross Revenue", "Contribution (%)"],
                this.state.revenueOutlets.map((r) => [r.category, r.gross, r.percent]),
            );
        } else {
            this._downloadCsv(
                "reso_ownership_yield_report.csv",
                ["Shareholder", "Property", "Ownership (%)", "Dividend", "Status"],
                this.state.ownershipYields.map((r) => [r.name, r.property, r.percent, r.dividend, r.status]),
            );
        }
    }
}

registry.category("actions").add("reso_pms.analytics_dashboard", ResoAnalyticsDashboard);
