# Phased Implementation Plan
## Architecture package — item 20

> Master document: [`architecture.md`](architecture.md). Build strictly in dependency order
> (§71–§72). Each phase is a **thin vertical slice**: a small, valuable, testable increment that is
> wired end-to-end (UI + API + domain + DB + validation + authorization + workflow + audit + tests)
> — not a screen-only stub (§79).

---

## Phase map

| # | Phase | Outcome | Exit criteria (feature-complete per §79) |
| --- | --- | --- | --- |
| 1 | **Foundation** | auth, users, roles, permissions, database, audit, document infra, navigation, design system | login/logout/session; RBAC enforced server-side; audit log on mutations; document upload/download with access control |
| 2 | **Core coordination** | task engine, task templates, scheduler, workflows, notifications, escalation, calendar, dashboard | recurring work auto-materialises; ladder/escalation fire; officer dashboard shows real attention queues |
| 3 | **Property management** | properties, units, applications, tenants, leases, occupancy | application→approval→lease→occupancy chain works end-to-end with enforced states |
| 4 | **Rent** | invoices, payments, receipts, tenant ledger, arrears, deposits | invoice→payment→ledger→receipt; arrears buckets + 30/60/90 escalation; append-only ledger |
| 5 | **Maintenance** | tickets, requests, inspections, defects, contractors, work orders, SLA | request→work order→completion→verification→closure; inspection→defect→request chain |
| 6 | **Farm** | crop, livestock, workforce, attendance, duties, farm activities | daily livestock/attendance/crop tasks auto-generate and verify; attendance export |
| 7 | **Stock / Assets / Procurement** | stock, counts, variance, reorder, assets, audits, suppliers, procurement | count→variance→investigation; reorder→request draft; asset audit→missing investigation; procurement approval (configured thresholds) |
| 8 | **Incidents / Compliance / Records** | incidents, escalation, compliance calendar, document management, communications | incident severity escalation; compliance reminders; central docs + comms history |
| 9 | **Reporting** | dashboards, reports, report scheduler, report archive | daily/weekly/monthly/quarterly reports auto-generate from live data and archive |
| 10 | **Integrations** | WhatsApp, email, SMS, payments, e-signature, accounting export (adapters) | only integrations with real credentials go live; each behind an adapter + webhook idempotency |

---

## Dependency-ordered build sequence (§72)

```text
PHASE 1  AUTH → USERS/ROLES/PERMISSIONS → AUDIT → DATABASE/DOMAIN MODEL
                                              ├→ DOCUMENTS
                                              └→ EVENT ENGINE
PHASE 2  TASK ENGINE → TASK TEMPLATES → SCHEDULER → SLA → NOTIFICATIONS → ESCALATIONS
PHASE 3  PROPERTY → UNIT → TENANT → LEASE
PHASE 4  RENT
PHASE 5  MAINTENANCE → INSPECTION
PHASE 6  FARM → CROP · LIVESTOCK · WORKFORCE
PHASE 7  STOCK → PROCUREMENT · ASSETS
PHASE 8  INCIDENTS · COMPLIANCE
PHASE 9  REPORTING/ANALYTICS → DASHBOARDS
PHASE 10 INTEGRATION ADAPTERS (only with real credentials)
```

## Delivery mechanics

- **One domain per increment**; a domain ships only when its dependency chain exists.
- **Definition of done** (§79): UI + API + domain logic + database + validation + authorization +
  workflow + audit + tests are connected and passing.
- **Demo data:** clearly isolated as development-only; never treated as production (§56). Production
  seed = roles, permissions, statuses, priorities, categories **only** — no fabricated tenants,
  payments, properties, leases, workers, livestock, stock, or incidents.
- **Gate reviews** after Phase 2 (automation core) and Phase 5 (tenancy + rent + maintenance) — the
  two highest-risk boundaries — before continuing.

## Key decision gates (must be answered before the phase that needs them)

| Decision | Needed by | Class |
| --- | --- | --- |
| Procurement approval thresholds | Phase 7 | `DECISION_REQUIRED` |
| WhatsApp provider | Phase 10 (earlier for capture pilot) | `DECISION_REQUIRED` |
| Payment method(s): bank / M-Pesa / EcoCash | Phase 4 (reconciliation), 10 | `DECISION_REQUIRED` |
| E-signature provider + legal validity | Phase 3 (lease signing) | `DECISION_REQUIRED` |
| Statutory retention periods | Phase 1 (records config) | `DECISION_REQUIRED` |
| Compliance obligations list | Phase 8 | `DECISION_REQUIRED` |
| Interface language (en/st/both) | Phase 1 (i18n) | `INFERRED` (en+st) |

Full register: [`assumptions.md`](assumptions.md).

---

*Next in package: [`assumptions.md`](assumptions.md).*
