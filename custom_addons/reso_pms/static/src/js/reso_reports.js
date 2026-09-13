/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ResoAnalyticsDashboard extends Component {
    static template = "reso_pms.ResoReportsTemplate";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            activeTab: "occupancy",
            occupancyData: [
                { month: "Jan 2026", occupancy: 65.4, adr: 12000, revpar: 7848, status: "Normal" },
                { month: "Feb 2026", occupancy: 72.1, adr: 12500, revpar: 9012, status: "Normal" },
                { month: "Mar 2026", occupancy: 80.5, adr: 13000, revpar: 10465, status: "High Season" },
                { month: "Apr 2026", occupancy: 78.2, adr: 13500, revpar: 10557, status: "Normal" },
                { month: "May 2026", occupancy: 85.0, adr: 14000, revpar: 11900, status: "High Season" },
                { month: "Jun 2026", occupancy: 88.4, adr: 15000, revpar: 13260, status: "High Season" },
                { month: "Jul 2026", occupancy: 92.1, adr: 16500, revpar: 15196, status: "High Season" },
                { month: "Aug 2026", occupancy: 89.5, adr: 15500, revpar: 13872, status: "High Season" },
                { month: "Sep 2026", occupancy: 84.0, adr: 14500, revpar: 12180, status: "High Season" },
            ],
            revenueOutlets: [
                { category: "Room Accommodation & Villas", gross: "12,500,000", vat: "1,875,000", net: "10,625,000", percent: "68.5%" },
                { category: "Food & Beverage / Restaurant POS", gross: "3,800,000", vat: "570,000", net: "3,230,000", percent: "20.8%" },
                { category: "Spa & Wellness Center", gross: "1,200,000", vat: "180,000", net: "1,020,000", percent: "6.6%" },
                { category: "Excursions, Tours & Water Sports", gross: "750,000", vat: "112,500", net: "637,500", percent: "4.1%" },
            ],
            ownershipYields: [
                { name: "Prospire Investments Group", property: "Baliyari Resort Cox Beach", shares: 20, percent: "20.0%", dividend: "3,000,000", status: "Processed" },
                { name: "Kazi Zainul Abedin", property: "Baliyari Resort Cox Beach", shares: 5, percent: "5.0%", dividend: "750,000", status: "Processed" },
                { name: "Mahbubur Rahman", property: "Baliyari Hill Resort Sreemangal", shares: 10, percent: "10.0%", dividend: "1,500,000", status: "Processed" },
            ]
        });
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    exportReport(reportName) {
        alert(`Exporting ${reportName} from resoERP...`);
    }
}

registry.category("actions").add("reso_pms.analytics_dashboard", ResoAnalyticsDashboard);
