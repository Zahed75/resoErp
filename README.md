# resoERP — Multi-Property Resort Management & Fractional Ownership Platform

**resoERP** is a unified, Enterprise-grade Odoo 19 ERP solution designed for resort operators, hotel groups, and fractional ownership managers in Bangladesh and internationally.

---

## 🏗️ Architecture & Stack

- **Platform**: Odoo 19.0 Enterprise, Python 3.11+, PostgreSQL 15+.
- **Custom Apps (`custom_addons/`)**:
  - `reso_pms`: Multi-Property Management System, Room Inventory, Rate Plans, Availability Engine, Folio & Outlet Charges, Housekeeping Board, Maintenance Ticketing, Stock & Supplies, HR Shifts, CAPEX Projects, CRM Lead Pipelines, WhatsApp Automation, and Document/KYC Management.
  - `reso_ownership`: Fractional Shareholder Registry, Approval-based Share Transfers, Dividend Distribution Engine.
- **Native User Interface & Dashboards**:
  - Native Odoo OWL Executive Dashboard (`reso_pms.executive_dashboard`) and Analytics & Reports Center (`reso_pms.analytics_dashboard`).
  - Styled with Reso Dark Glassmorphism SCSS (`reso_dashboard.scss`).

---

## 🛠️ Installation & Setup

Activate your Python virtual environment and run Odoo:
```bash
source env/bin/activate
python3 odoo-bin -c odoo.conf
```
Or use the helper script:
```bash
./run_odoo.sh
```
Access Odoo ERP at `http://localhost:8069`. All dashboards and features are available directly inside Odoo Web Client under **Reso PMS**.

---

## 🔌 REST & Webhook API Endpoints

- `GET /api/v1/pms/dashboard/summary` — Executive Dashboard KPI summary.
- `GET /api/v1/pms/bookings` — Reservation list and status.
- `GET /api/v1/pms/rooms` — Live room inventory and housekeeping status.
- `PUT /api/v1/pms/rooms/<id>/housekeeping` — Housekeeping status update.
- `GET /api/v1/website/properties` — Public property & room type listings.
- `POST /api/v1/website/availability` — Real-time availability calculation.
- `POST /api/v1/website/booking/create` — Direct online booking creation.
- `GET/POST /api/v1/payment/process` — bKash, Nagad, SSLCommerz, and Stripe payment handler.
- `POST /api/v1/whatsapp/webhook` — 2-Way WhatsApp messaging & FAQ Chatbot.

---

## 🧪 Unit Tests
Run Odoo test suite for custom modules:
```bash
python3 odoo-bin --addons-path=custom_addons,odoo/addons --test-enable -d test_reso_db -i reso_pms,reso_ownership --stop-after-init
```

# resoErp
