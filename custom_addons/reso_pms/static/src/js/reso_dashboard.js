/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ResoExecutiveDashboard extends Component {
    static template = "reso_pms.ResoDashboardTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            selectedPropertyId: "all",
            properties: [],
            kpis: {
                totalRooms: 0,
                occupiedRooms: 0,
                dirtyRooms: 0,
                maintenanceRooms: 0,
                occupancyRate: 0,
                checkinsToday: 0,
                checkoutsToday: 0,
                totalRevenue: 0,
                adr: 0,
                revpar: 0,
                currencySymbol: "BDT",
                fractionalOwners: 0,
                fractionalUnits: 0,
            },
            rooms: [],
            bookings: [],
        });

        onWillStart(async () => {
            await this.loadProperties();
            await this.loadDashboardData();
        });
    }

    async loadProperties() {
        try {
            const props = await this.orm.searchRead("reso.property", [["active", "=", true]], ["id", "name"]);
            this.state.properties = props;
        } catch (e) {
            console.error("Error loading properties:", e);
        }
    }

    async loadDashboardData() {
        const propDomain = this.state.selectedPropertyId !== "all" 
            ? [["property_id", "=", parseInt(this.state.selectedPropertyId)]] 
            : [];

        try {
            // Load Rooms
            const roomFields = ["id", "name", "property_id", "room_type_id", "status", "housekeeping_status", "housekeeper_id"];
            const rooms = await this.orm.searchRead("reso.room", propDomain, roomFields, { limit: 20 });
            this.state.rooms = rooms.map(r => ({
                id: r.id,
                name: r.name,
                property: r.property_id ? r.property_id[1] : "",
                room_type: r.room_type_id ? r.room_type_id[1] : "",
                status: r.status,
                housekeeping_status: r.housekeeping_status,
                housekeeper: r.housekeeper_id ? r.housekeeper_id[1] : "Unassigned",
            }));

            // Load KPI Aggregates
            const allRoomsCount = await this.orm.searchCount("reso.room", [["active", "=", true], ...propDomain]);
            const occupiedRoomsCount = await this.orm.searchCount("reso.room", [["status", "=", "occupied"], ...propDomain]);
            const dirtyRoomsCount = await this.orm.searchCount("reso.room", [["housekeeping_status", "=", "dirty"], ...propDomain]);
            const maintenanceRoomsCount = await this.orm.searchCount("reso.room", [["status", "=", "maintenance"], ...propDomain]);

            const todayStr = new Date().toISOString().split("T")[0];
            const checkinsToday = await this.orm.searchCount("reso.booking", [["checkin_date", "=", todayStr], ...propDomain]);
            const checkoutsToday = await this.orm.searchCount("reso.booking", [["checkout_date", "=", todayStr], ...propDomain]);

            // Load Recent Bookings
            const bookingFields = ["id", "name", "partner_id", "property_id", "room_type_id", "room_id", "checkin_date", "checkout_date", "state", "amount_total", "currency_id"];
            const bookings = await this.orm.searchRead("reso.booking", propDomain, bookingFields, { limit: 10, order: "checkin_date desc" });
            this.state.bookings = bookings.map(b => ({
                id: b.id,
                name: b.name,
                guest: b.partner_id ? b.partner_id[1] : "",
                property: b.property_id ? b.property_id[1] : "",
                room_type: b.room_type_id ? b.room_type_id[1] : "",
                room: b.room_id ? b.room_id[1] : "Unassigned",
                checkin_date: b.checkin_date,
                checkout_date: b.checkout_date,
                state: b.state,
                amount_total: b.amount_total,
                currency: b.currency_id ? b.currency_id[1] : "BDT",
            }));

            // Revenue Stats
            const totalRevenue = bookings.reduce((sum, b) => sum + (b.amount_total || 0), 0);
            const occupancyRate = allRoomsCount > 0 ? ((occupiedRoomsCount / allRoomsCount) * 100).toFixed(1) : 0;
            const adr = bookings.length > 0 ? (totalRevenue / bookings.length).toFixed(0) : 0;
            const revpar = allRoomsCount > 0 ? (totalRevenue / allRoomsCount).toFixed(0) : 0;

            // Fractional Owners Count
            let ownersCount = 0;
            try {
                ownersCount = await this.orm.searchCount("reso.owner.registry", propDomain);
            } catch (e) {
                ownersCount = 0;
            }

            this.state.kpis = {
                totalRooms: allRoomsCount,
                occupiedRooms: occupiedRoomsCount,
                dirtyRooms: dirtyRoomsCount,
                maintenanceRooms: maintenanceRoomsCount,
                occupancyRate: occupancyRate,
                checkinsToday: checkinsToday,
                checkoutsToday: checkoutsToday,
                totalRevenue: totalRevenue,
                adr: adr,
                revpar: revpar,
                currencySymbol: "BDT",
                fractionalOwners: ownersCount,
                fractionalUnits: ownersCount * 4,
            };
        } catch (e) {
            console.error("Error loading dashboard data:", e);
        }
    }

    async onPropertyChange(ev) {
        this.state.selectedPropertyId = ev.target.value;
        await this.loadDashboardData();
    }

    async markClean(roomId, ev) {
        ev.stopPropagation();
        try {
            await this.orm.call("reso.room", "action_mark_clean", [[roomId]]);
            await this.loadDashboardData();
        } catch (e) {
            console.error("Error marking clean:", e);
        }
    }

    async refreshData() {
        await this.loadDashboardData();
    }

    getInitials(name) {
        if (!name) return "?";
        const parts = name.trim().split(/\s+/);
        return parts.length > 1
            ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
            : parts[0].slice(0, 2).toUpperCase();
    }

    openRoom(roomId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "reso.room",
            res_id: roomId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openBooking(bookingId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "reso.booking",
            res_id: bookingId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNewBooking() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "reso.booking",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllRooms() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Rooms Board",
            res_model: "reso.room",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("reso_pms.executive_dashboard", ResoExecutiveDashboard);
