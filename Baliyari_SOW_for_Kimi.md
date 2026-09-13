# Statement of Work & Technical Build Specification
## Baliyari Resort Management System — Odoo 19 Enterprise, Multi-Property Resort & Hotel ERP Platform

Prepared by: Syscomatic LLC / ProspireNext | Date: September 13, 2026 | Version 1.0

---

## 1. Executive Summary

Baliyari Resort requires a unified, ERP-driven platform to run every operational, commercial, and ownership function of a resort/hotel business — booking and guest experience, property and housekeeping operations, F&B and retail, finance, HR, maintenance, document control, fractional ownership administration, and WhatsApp-based guest and investor communication.

This solution is built on Odoo 19 Enterprise, engineered from day one as a reusable, configurable product — not a single-client build — so it can be deployed for any resort or hotel operator, in Bangladesh or internationally, with property-specific configuration rather than code forks. The native Odoo web client is used wherever it meets the need; a custom front end (Material UI on React, or Angular 21 where an Angular-first stack is required) is reserved for guest-facing and owner-facing experiences that need a distinct brand and UX beyond Odoo's website builder.

## 2. Project Objectives

- Deliver a single source of truth across booking, operations, finance, HR, and ownership.
- Design every module as multi-property and multi-tenant capable.
- Enable direct, commission-free online booking with real-time rate/availability sync.
- Automate guest and investor communication end-to-end through WhatsApp.
- Provide transparent fractional ownership administration with full audit trail.
- Ensure compliance with Bangladesh data-privacy expectations and GDPR for international deployments.
- Keep the core on standard, upgrade-safe Odoo 19 Enterprise APIs.

## 3. Product Vision — Built for Reuse

- **Property abstraction**: every module keys off a Property record (multi-company or custom property dimension), supporting one resort or a portfolio under one or many legal entities.
- **Configuration over customization**: room types, rate plans, owner classes, tax rules, messaging templates are data-driven, editable without code changes.
- **Localization layer**: currency, tax (VAT/BIN for Bangladesh or destination-country tax), language (Bangla/English, extensible), payment gateway — all pluggable per deployment.
- **Packaging**: custom modules (PMS extensions, Fractional Ownership, WhatsApp connector) built as independently installable Odoo apps for reuse across other hotel groups.

## 4. Scope of Services

### 4.1 Odoo ERP Modules

| Module | Core Functional Scope | Key Odoo Apps / Approach |
|---|---|---|
| Website & Online Booking | Room/villa listing, real-time availability, rate display, direct booking checkout, guest account portal, online appointments for tours/spa | Website, eCommerce, Online Appointments |
| Hotel/Property Mgmt (PMS) | Room & villa inventory, room types, rate plans/seasonal pricing, availability calendar, check-in/out workflow, housekeeping status board, maintenance tickets | Custom PMS module built on Odoo (Sales, Calendar, Maintenance) or community Hotel Management extension, rebuilt for Enterprise-grade multi-property use |
| Sales & CRM | Guest & investor pipelines, lead scoring, campaigns, follow-up automation, email/WhatsApp sequences, corporate/agent rate contracts | CRM, Sales, Email Marketing, Marketing Automation |
| Inventory & Procurement | F&B stock, housekeeping/amenity supplies, maintenance parts, multi-warehouse per property, vendor management, auto purchase on reorder | Inventory, Purchase |
| Point of Sale | Restaurant, bar, spa, retail outlet billing; split/room-charge billing to guest folio; kitchen order tickets | POS Restaurant, POS |
| Accounting & Finance | Guest folio invoicing, multi-currency payments, bank reconciliation, revenue reporting by property/outlet, owner/shareholder distribution statements | Accounting, Invoicing |
| Human Resources | Employee records, shift scheduling, attendance/biometric integration, payroll, appraisal & performance tracking | Employees, Attendance, Payroll, Appraisals |
| Project & Task Mgmt | Preventive & corrective maintenance scheduling, renovation/CAPEX projects, internal workflow tasks with SLA tracking | Project, Maintenance, Planning |
| Document Management | Secure storage of contracts, guest ID/KYC docs, legal files, share certificates, role-based access, retention policy | Documents, Sign |
| Fractional Ownership | Owner/shareholder registry, fraction/unit ledger, transfer workflow with approval, income distribution engine, owner communications & statements | Custom module integrated with CRM, Accounting, Documents, Sign |

### 4.2 WhatsApp Integration

**Automated Messaging**
- Booking confirmations, pre-arrival reminders, check-in/check-out instructions, post-stay feedback requests.
- Investor/shareholder notifications: distribution statements, AGM/announcement broadcasts, ownership-transfer confirmations.

**Two-Way Chat**
- Front-desk, concierge, and sales teams reply from Odoo Discuss/CRM, with conversation history attached to the guest or partner record.
- Integration via an official Odoo WhatsApp connector or a certified BSP (Twilio, Gupshup, or 360dialog/Chat API), selected based on Bangladesh message-rate and template-approval requirements.

**Chatbot / FAQ Automation**
- Rule-based or LLM-assisted first-response bot for booking status, amenities, check-in times, ownership FAQs, with handoff to a human agent on low confidence.

**CRM Logging & Compliance**
- Every inbound/outbound WhatsApp message logged against the guest or investor partner record.
- Opt-in/opt-out capture, message retention limits, data-subject access/erasure workflows for GDPR (international guests) and Bangladesh data-protection expectations.

### 4.3 Frontend / UI Strategy

- Default: Odoo's native backend and Website/eCommerce front end for admin, staff, and standard booking flows.
- Where a distinct, branded guest portal, owner portal, or internal dashboard is required:
  - **Primary**: React + Material UI (MUI) — component-driven SPA consuming Odoo via JSON-RPC/XML-RPC or a custom REST/GraphQL layer.
  - **Alternative**: Angular 21 + Angular Material — used where an Angular-first stack is explicitly required; component structure should mirror the MUI build so both share the same backend API contract.
  - Both talk to Odoo through a documented API layer (Section 5), never direct ORM access.

## 5. Technical Architecture

**Backend**
- Odoo 19.0 Enterprise, Python 3.11+, PostgreSQL 15+.
- Custom modules namespaced under a single vendor prefix (e.g. `baliyari_pms`, `baliyari_ownership`, `baliyari_whatsapp`) for clean packaging and reuse.
- REST/GraphQL API layer exposed via Odoo controllers for the custom front end and third-party integrations.

**Frontend**
- Odoo native web client for internal operations (PMS console, housekeeping board, HR, accounting).
- React + MUI (or Angular 21 + Angular Material) SPA for the public booking site, guest self-service portal, and owner portal — deployed independently, integrated via API + SSO.

**Integrations**
- Payment gateways (local: bKash/Nagad/SSLCommerz; international: Stripe/PayPal).
- WhatsApp Business Platform via connector/BSP.
- Optional channel manager (Booking.com, Agoda, Airbnb) for OTA rate/availability sync.
- Biometric/attendance device integration for HR.

**Environments & DevOps**
- Separate dev, staging, production Odoo instances; automated module tests run in CI before promotion.
- Database-per-tenant or multi-company-per-database strategy decided in Discovery.

## 6. Non-Functional Requirements

- Multi-property / multi-tenant ready from the first release.
- Role-based access control down to property, module, and record level.
- Data protection: encryption in transit and at rest for documents/KYC data; audit log on financial and ownership records.
- Compliance: GDPR-aligned data subject rights + Bangladesh data-privacy/e-commerce regulations.
- Performance: booking/availability queries under 2 seconds under normal load; horizontal scalability.
- Localization: Bangla and English UI minimum, configurable currency/tax per deployment.
- Backup & disaster recovery: automated daily backups with tested restore procedure.

## 7. Deliverables

1. Configured and customized Odoo 19 Enterprise instance covering all Section 4.1 modules.
2. Custom Odoo apps: PMS extension, Fractional Ownership & Investor Management, WhatsApp Connector.
3. Public booking website with online payment.
4. Guest and Owner self-service portals.
5. WhatsApp automation flows, chatbot, two-way chat integration.
6. Data migration from existing records.
7. Technical documentation: data model, API contract, module structure, deployment guide.
8. User documentation and training.
9. UAT sign-off report and 4-week hypercare/support period post go-live.

## 8. Assumptions & Exclusions

**Assumptions**
- Client provides property, room, rate, and existing guest/owner data for migration.
- Odoo 19 Enterprise licensing procured by client (or via implementation partner).
- WhatsApp Business Platform account and template approvals are client's responsibility, with implementation support provided.
- Hosting infrastructure provisioned separately unless included in a signed hosting addendum.

**Exclusions (unless separately scoped)**
- Physical hardware procurement (POS terminals, biometric devices, card readers).
- Legal drafting of ownership/fractional-share contracts.
- Marketing content creation for the booking website.

## 9. Project Phases & High-Level Timeline

| Phase | Duration (indicative) | Key Activities |
|---|---|---|
| 1. Discovery & Blueprint | 2–3 weeks | Requirement workshops, process mapping, data model design, wireframes, environment setup |
| 2. Core PMS & Website | 4–6 weeks | Property/room/rate model, booking engine, website integration, payment gateway, availability sync |
| 3. Operations Modules | 4–6 weeks | Housekeeping, maintenance, inventory/procurement, POS integration, HR & payroll |
| 4. Finance & Ownership | 3–4 weeks | Accounting configuration, guest folio billing, fractional ownership module, distribution engine |
| 5. WhatsApp & Automation | 2–3 weeks | Connector setup, messaging flows, two-way chat, chatbot/FAQ, CRM logging |
| 6. UAT, Migration & Go-Live | 2–4 weeks | UAT, data migration, training, staged rollout, hypercare |

Total indicative duration: 17–26 weeks depending on final scope confirmation and client resource availability during UAT.

## 10. Acceptance Criteria

- Each module in Section 4.1 passes documented UAT test cases signed off by the client's approver.
- A test booking can be made end-to-end on the public website, paid, confirmed, and reflected in the PMS and accounting.
- A WhatsApp booking confirmation and a two-way chat message are logged against the correct guest record.
- An investor distribution statement is generated correctly for a sample ownership fraction and delivered via WhatsApp/email.
- System performs within Section 6 response-time targets under agreed concurrent-user load.

---

ROLE
You are a senior Odoo 19 Enterprise developer and solution architect.
Build a production-grade, reusable Resort/Hotel Management ERP called
"Baliyari Resort Management System", deployable for any resort or
hotel operator worldwide, and specifically for Bangladeshi operators
(local tax/payment/WhatsApp compliance).

STACK
- Backend: Odoo 19.0 Enterprise, Python 3.11+, PostgreSQL 15+.
- Custom addons namespaced: baliyari_pms, baliyari_ownership,
  baliyari_whatsapp, baliyari_portal_api.
- Frontend (only where native Odoo Website/portal is insufficient):
  React 18 + MUI v5 as the default; Angular 21 + Angular Material as
  the alternative stack when explicitly required. Both consume a
  documented REST/GraphQL API exposed from Odoo controllers — never
  access the ORM directly from the frontend.
- Integrations: WhatsApp Business Platform (via Odoo WhatsApp
  connector or Twilio/Gupshup/360dialog), local payment gateways
  (bKash/Nagad/SSLCommerz) plus Stripe/PayPal, optional OTA channel
  manager.

BUILD ORDER
1. Data model: Property, RoomType, Room/Villa, RatePlan, Booking,
   OwnerShareRegistry, ShareTransfer, DistributionRun.
2. PMS core: availability engine, rate calendar, booking lifecycle
   (hold -> confirmed -> checked-in -> checked-out -> invoiced),
   housekeeping status board, maintenance ticketing.
3. Website & eCommerce booking flow with payment capture.
4. Sales/CRM pipelines for guests (leads) and investors, with
   campaign and follow-up automation.
5. Inventory/Procurement for F&B, housekeeping, maintenance stock;
   vendor management and reorder rules.
6. POS integration for restaurant/bar/retail with room-charge
   posting to guest folio.
7. Accounting: folio invoicing, multi-currency, reconciliation,
   revenue-by-property reporting, owner distribution statements.
8. HR: employee records, attendance, scheduling, payroll,
   performance reviews.
9. Project/Task module for renovation and maintenance workflows.
10. Document management for contracts, KYC, legal files, share
    certificates, with role-based access and retention rules.
11. Fractional Ownership module: owner registry, fraction ledger,
    approval-based transfer workflow, distribution engine, owner
    communication log.
12. WhatsApp connector: templated automated messages, two-way
    chat surfaced in Discuss/CRM, chatbot/FAQ with human handoff,
    full message logging on guest/partner records, opt-in/opt-out
    and retention controls for GDPR + Bangladesh compliance.
13. Optional custom portal (React+MUI or Angular 21) for guest
    self-service and owner self-service, built against the API
    layer from step 1-12, not against the ORM.

NON-NEGOTIABLE CONSTRAINTS
- Every module must work for an arbitrary number of properties
  (multi-property/multi-company), configured via data, not code.
- No hard-coded currency, tax, or language — pull from deployment
  configuration.
- All custom modules must pass Odoo's standard module test suite
  and be independently installable/uninstallable.
- Follow Odoo OWL/JS and Python coding guidelines for Enterprise
  addons so the solution remains upgrade-safe across Odoo versions.
- Write unit and integration tests for booking lifecycle, folio
  billing, and the ownership distribution engine before marking
  any of those three complete.

OUTPUT EXPECTED FROM YOU AT EACH STEP
- The addon(s) for that step, with manifest, models, views, and
  tests.
- A short migration/upgrade note if the step changes existing
  data models.
- A one-paragraph summary of what was built and what remains.
```
