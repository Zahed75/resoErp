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
            ownershipInstalled: false,
            kpis: {
                totalRooms: 0,
                occupiedRooms: 0,
                dirtyRooms: 0,
                maintenanceRooms: 0,
                occupancyRate: 0,
                checkinsToday: 0,
                checkoutsToday: 0,
                lateCheckouts: 0,
                inProgressBookings: 0,
                totalRevenue: 0,
                adr: 0,
                revpar: 0,
                currencySymbol: "BDT",
                fractionalOwners: null,
                openTickets: 0,
                lowStockItems: 0,
                openLeads: 0,
            },
            rooms: [],
            bookings: [],
            tickets: [],
            messages: [],
        });

        this.quickLinks = [
            { label: "Bookings", icon: "fa-ticket", model: "reso.booking", color: "primary" },
            { label: "Rooms Board", icon: "fa-bed", model: "reso.room", color: "info" },
            { label: "Rate Plans", icon: "fa-tags", model: "reso.rate.plan", color: "success" },
            { label: "Maintenance", icon: "fa-wrench", model: "reso.maintenance.ticket", color: "danger" },
            { label: "Stock & Supplies", icon: "fa-cubes", model: "reso.stock.supply", color: "warning" },
            { label: "HR Shifts", icon: "fa-id-badge", model: "reso.hr.shift", color: "info" },
            { label: "CAPEX Projects", icon: "fa-building", model: "reso.capex.project", color: "primary" },
            { label: "Documents & KYC", icon: "fa-folder", model: "reso.document", color: "success" },
            { label: "WhatsApp Logs", icon: "fa-whatsapp", model: "reso.whatsapp.message", color: "success" },
            { label: "Investor Leads", icon: "fa-users", model: "crm.lead", color: "warning" },
            { label: "Owner Registry", icon: "fa-pie-chart", model: "reso.owner.registry", color: "primary", ownershipOnly: true },
            { label: "Distribution Runs", icon: "fa-money", model: "reso.distribution.run", color: "info", ownershipOnly: true },
        ];

        onWillStart(async () => {
            await this.loadProperties();
            await this.loadDashboardData();
        });
    }

    get visibleQuickLinks() {
        return this.quickLinks.filter(l => !l.ownershipOnly || this.state.ownershipInstalled);
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
            // All KPIs in a single backend call (real ADR/RevPAR math, 30-day window)
            const stats = await this.orm.call(
                "reso.booking", "get_dashboard_stats",
                [this.state.selectedPropertyId !== "all" ? parseInt(this.state.selectedPropertyId) : null]);

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
                amount_total: Number(b.amount_total || 0).toLocaleString("en-US"),
                currency: b.currency_id ? b.currency_id[1] : "BDT",
            }));

            // Recent Maintenance Tickets
            const tickets = await this.orm.searchRead("reso.maintenance.ticket",
                [["state", "in", ["new", "in_progress"]]],
                ["id", "name", "title", "priority", "state", "room_id"],
                { limit: 5, order: "priority desc, request_date desc" });
            this.state.tickets = tickets.map(t => ({
                id: t.id,
                name: t.name,
                title: t.title,
                priority: t.priority,
                state: t.state,
                room: t.room_id ? t.room_id[1] : "",
            }));

            // Recent WhatsApp Messages
            const messages = await this.orm.searchRead("reso.whatsapp.message",
                [], ["id", "partner_id", "body", "message_type", "state"],
                { limit: 5, order: "create_date desc" });
            this.state.messages = messages.map(m => ({
                id: m.id,
                partner: m.partner_id ? m.partner_id[1] : "",
                body: m.body,
                message_type: m.message_type,
                state: m.state,
            }));

            this.state.ownershipInstalled = stats.ownership_installed;
            this.state.kpis = {
                totalRooms: stats.rooms_total,
                occupiedRooms: stats.rooms_occupied,
                dirtyRooms: stats.rooms_dirty,
                maintenanceRooms: stats.rooms_maintenance,
                occupancyRate: stats.occupancy_rate,
                checkinsToday: stats.arrivals_today,
                checkoutsToday: stats.departures_today,
                lateCheckouts: stats.late_checkouts,
                inProgressBookings: stats.in_house,
                totalRevenue: Number(stats.revenue_30d || 0).toLocaleString("en-US"),
                adr: Number(stats.adr || 0).toLocaleString("en-US"),
                revpar: Number(stats.revpar || 0).toLocaleString("en-US"),
                currencySymbol: stats.currency_symbol || stats.currency || "",
                fractionalOwners: stats.fractional_owners,
                openTickets: stats.open_tickets,
                lowStockItems: stats.low_stock,
                openLeads: stats.open_leads,
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

    openQuickLink(model, label) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: label,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
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
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTicket(ticketId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "reso.maintenance.ticket",
            res_id: ticketId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("reso_pms.executive_dashboard", ResoExecutiveDashboard);
