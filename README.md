# resoERP — Multi-Property Resort Management & Fractional Ownership Platform

**resoERP** is a unified, Enterprise-grade Odoo 19 ERP solution designed for resort operators, hotel groups, and fractional ownership managers in Bangladesh and internationally.

---

## 🏗️ Architecture & Stack

- **Platform**: Odoo 19.0 Enterprise, Python 3.11+, PostgreSQL 15+.
- **Custom Apps (`custom_addons/`)**:
  - `reso_pms`: Multi-Property Management System, Room Inventory, Rate Plans, Availability Engine, Folio & Outlet Charges, Housekeeping Board, Maintenance Ticketing, Stock & Supplies, HR Shifts, CAPEX Projects, CRM Lead Pipelines, WhatsApp Automation, and Document/KYC Management.
  - `reso_ownership`: Fractional Shareholder Registry, Approval-based Share Transfers, Dividend Distribution Engine.
- **Native User Interface & Dashboards**:
  - Native Odoo OWL Executive Dashboard (`reso_pms.executive_dashboard`) — the default landing screen with KPI strip, complete solution quick-links, housekeeping board, bookings, maintenance & WhatsApp activity feeds.
  - Analytics & Reports Center (`reso_pms.analytics_dashboard`).
  - Modern light theme with dynamic dark-mode support (follows Odoo's own dark mode toggle).
- **Public Booking Website (`/resort`)**:
  - Built natively in Odoo (QWeb + `web.assets_frontend`) — no separate frontend app.
  - "Liquid glass" modern design: animated gradient blobs, glassmorphism cards, scroll-reveal animations, and a light/dark theme toggle persisted in the browser.
  - Pages: Home (`/resort`), Rooms & Villas (`/resort/rooms`), Book Now (`/resort/book`), Contact (`/resort/contact`), Booking Confirmation (`/resort/booking/confirmation`).

---

## 🛠️ Installation & Setup (Local, Python venv)

Activate your Python virtual environment and run Odoo:
```bash
source env/bin/activate
python3 odoo-bin -c odoo.conf
```
Or use the helper script:
```bash
./run_odoo.sh
```
Access Odoo ERP at `http://localhost:8069` and the public booking site at `http://localhost:8069/resort`.

To load demo data for local testing, install/update the modules with demo data enabled:
```bash
python3 odoo-bin -c odoo.conf -d resoSolution --without-demo=False -i reso_pms,reso_ownership --stop-after-init
```

---

## 🐳 Docker Deployment (aaPanel / any Linux VPS)

This repo ships with a `Dockerfile` and `docker-compose.yml` that bundle the full Odoo 19 source, `custom_addons/`, and PostgreSQL 15.

1. Copy the environment template and adjust credentials:
   ```bash
   cp .env.example .env
   ```
2. Build and start the stack:
   ```bash
   docker compose up -d --build
   ```
3. The first boot auto-installs `reso_pms` and `reso_ownership` (via `INIT_MODULES` in `.env`). Watch progress with:
   ```bash
   docker compose logs -f web
   ```
4. Odoo will be reachable on `http://<server-ip>:8069` (configurable via `HTTP_PORT` in `.env`).

### aaPanel reverse proxy
In aaPanel, create a website/domain and use the **Reverse Proxy** feature pointing to `127.0.0.1:8069` (the `proxy_mode = True` setting in `docker/odoo.conf` ensures Odoo correctly reads `X-Forwarded-*` headers from aaPanel's Nginx). Then issue a free SSL certificate for the domain directly from aaPanel's SSL tab.

To stop/rebuild:
```bash
docker compose down          # stop containers, keep data volumes
docker compose up -d --build # rebuild after pulling code changes
```

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
