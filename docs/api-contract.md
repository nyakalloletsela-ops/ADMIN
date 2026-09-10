# API Contract
## Architecture package — item 12

> Master document: [`architecture.md`](architecture.md). APIs are organised around **business
> capabilities**, not raw CRUD (§41). Every write is validated against a schema; every response is
> permission-scoped.

---

## 1. Conventions

- **Base path:** `/api/v1`
- **Auth:** bearer session token (`Authorization: Bearer …`); MFA-ready.
- **Format:** JSON (`application/json`).
- **Pagination:** `?page=&page_size=` → `{ items, page, page_size, total }`.
- **Idempotency:** mutating external/webhook calls accept `Idempotency-Key` header (or carry an
  event id); duplicates return the original result.
- **Correlation:** responses include `X-Correlation-Id`; errors echo it for tracing (§42).
- **Errors:** RFC-7807-style problem body:

```json
{ "type": "validation_error", "title": "Invalid input", "status": 422,
  "detail": "…", "correlation_id": "…", "errors": [ { "field": "due_date", "message": "…" } ] }
```

- **State changes** are intention-revealing sub-resources (e.g. `POST /tasks/{id}/verify`), not
  generic `PATCH status=` — the workflow engine validates the transition (§9).

---

## 2. Endpoint catalogue (by capability)

### Auth & identity

```text
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
POST   /api/auth/password-reset/request
POST   /api/auth/password-reset/confirm
GET    /api/auth/me
```

### Users, roles, permissions (admin)

```text
GET    /api/users
POST   /api/users
GET    /api/users/{id}
PATCH  /api/users/{id}
POST   /api/users/{id}/roles
GET    /api/roles
POST   /api/roles
GET    /api/permissions
```

### Dashboard

```text
GET    /api/dashboard                 // role-resolved KPIs + attention queues
GET    /api/dashboard/quick-actions   // permitted actions for the role
```

### Tasks & workplan

```text
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{id}
POST   /api/tasks/{id}/assign
POST   /api/tasks/{id}/start
POST   /api/tasks/{id}/block        { reason }
POST   /api/tasks/{id}/unblock
POST   /api/tasks/{id}/submit       { evidence_doc_ids? }
POST   /api/tasks/{id}/verify
POST   /api/tasks/{id}/reject       { reason }
POST   /api/tasks/{id}/complete
POST   /api/tasks/{id}/cancel       { reason }
POST   /api/tasks/{id}/escalate     { level }
POST   /api/tasks/{id}/follow-up    // spawn a follow-up task

GET    /api/task-templates
POST   /api/task-templates
PATCH  /api/task-templates/{id}
POST   /api/task-templates/{id}/activate | /deactivate

GET    /api/workplan                // calendar-view of materialised + planned work
GET    /api/calendar                // unified calendar (§34)
```

### Properties & units

```text
GET    /api/properties
POST   /api/properties
GET    /api/properties/{id}
PATCH  /api/properties/{id}
GET    /api/properties/{id}/units
POST   /api/properties/{id}/units
GET    /api/units/{id}
PATCH  /api/units/{id}
```

### Tenants & applications

```text
GET    /api/tenants
POST   /api/tenants
GET    /api/tenants/{id}            // 360° view
PATCH  /api/tenants/{id}
GET    /api/tenants/{id}/ledger
GET    /api/tenants/{id}/timeline

GET    /api/applications
POST   /api/applications
GET    /api/applications/{id}
POST   /api/applications/{id}/vet
POST   /api/applications/{id}/recommend
POST   /api/applications/{id}/approve | /reject
POST   /api/applications/{id}/offer
POST   /api/applications/{id}/accept | /decline
POST   /api/applications/{id}/move-in
```

### Leases

```text
GET    /api/leases
POST   /api/leases
GET    /api/leases/{id}
POST   /api/leases/{id}/submit       // DRAFT -> REVIEW
POST   /api/leases/{id}/send-for-signature
POST   /api/leases/{id}/activate
POST   /api/leases/{id}/renew        // human action; never auto
POST   /api/leases/{id}/terminate    // notice
POST   /api/leases/{id}/close
POST   /api/leases/{id}/archive
GET    /api/leases/expiring?within=90
```

### Rent & finance

```text
GET    /api/invoices
POST   /api/invoices                 // batch-generate for a billing period
GET    /api/invoices/{id}
POST   /api/invoices/{id}/payments   { amount, method, reference }
POST   /api/invoices/{id}/reverse    { reason }          // reversal, not delete
POST   /api/invoices/{id}/cancel     { reason }
GET    /api/arrears?bucket=31-60
POST   /api/deposits
POST   /api/deposits/{id}/refund     { amount }          // approval required
GET    /api/tenant-ledger/{tenant_id}
```

### Maintenance & inspections

```text
GET    /api/maintenance/requests
POST   /api/maintenance/requests
GET    /api/maintenance/requests/{id}
POST   /api/maintenance/requests/{id}/triage
POST   /api/maintenance/requests/{id}/cancel

GET    /api/work-orders
POST   /api/work-orders              { request_id, contractor_id, scope }
POST   /api/work-orders/{id}/assign
POST   /api/work-orders/{id}/start
POST   /api/work-orders/{id}/complete { evidence_doc_ids }
POST   /api/work-orders/{id}/verify
POST   /api/work-orders/{id}/close

GET    /api/contractors
POST   /api/contractors

GET    /api/inspections
POST   /api/inspections
POST   /api/inspections/{id}/start
POST   /api/inspections/{id}/submit   { checklist, findings[] }
POST   /api/inspections/{id}/close
GET    /api/inspection-templates
POST   /api/inspection-templates
```

### Farm operations

```text
GET    /api/farm/activities
GET    /api/farm/overview
GET    /api/crops
GET    /api/crop-plans
POST   /api/crop-plans
GET    /api/crop-activities
POST   /api/crop-activities/{id}/complete { evidence? }
GET    /api/livestock
POST   /api/livestock/records
GET    /api/livestock/records?date=
GET    /api/workers
POST   /api/workers
POST   /api/attendance
GET    /api/attendance?date=
POST   /api/attendance/{id}/verify
POST   /api/duties
GET    /api/rota?week=
```

### Stock, assets, procurement

```text
GET    /api/stock
POST   /api/stock/items
GET    /api/stock/items/{id}
GET    /api/stock/items/{id}/movements
POST   /api/stock/movements          { type: RECEIPT|ISSUE|TRANSFER|ADJUSTMENT }
GET    /api/stock/counts
POST   /api/stock/counts             // schedule/start
POST   /api/stock/counts/{id}/submit
POST   /api/stock/counts/{id}/reconcile
POST   /api/stock/counts/{id}/adjust // approval required
GET    /api/stock/variances

GET    /api/assets
POST   /api/assets
GET    /api/assets/{id}
POST   /api/assets/audits
POST   /api/assets/audits/{id}/complete

GET    /api/suppliers
POST   /api/suppliers
GET    /api/procurement/requests
POST   /api/procurement/requests
POST   /api/procurement/requests/{id}/review
POST   /api/procurement/requests/{id}/approve | /reject
POST   /api/procurement/requests/{id}/issue-po
POST   /api/purchase-orders
POST   /api/purchase-orders/{id}/order
POST   /api/purchase-orders/{id}/receive
POST   /api/purchase-orders/{id}/verify
```

### Incidents, service desk, compliance

```text
GET    /api/incidents
POST   /api/incidents
POST   /api/incidents/{id}/acknowledge
POST   /api/incidents/{id}/assign
POST   /api/incidents/{id}/resolve
POST   /api/incidents/{id}/verify
POST   /api/incidents/{id}/close
POST   /api/incidents/{id}/escalate

GET    /api/tickets
POST   /api/tickets
POST   /api/tickets/{id}/acknowledge
POST   /api/tickets/{id}/assign
POST   /api/tickets/{id}/respond
POST   /api/tickets/{id}/resolve
POST   /api/tickets/{id}/close
POST   /api/tickets/{id}/escalate

GET    /api/compliance
POST   /api/compliance/obligations
POST   /api/compliance/obligations/{id}/complete
```

### Records, documents, communications

```text
GET    /api/documents
POST   /api/documents               // multipart upload -> storage + metadata
GET    /api/documents/{id}/download // permission-scoped
POST   /api/documents/{id}/versions
GET    /api/documents/{id}/versions
GET    /api/communications?entity=tenant:123
GET    /api/timeline?entity=tenant:123
```

### Notifications, reports, search, audit, health

```text
GET    /api/notifications
POST   /api/notifications/{id}/ack
GET    /api/notification-rules
POST   /api/notification-rules
GET    /api/escalation-rules
POST   /api/escalation-rules

GET    /api/reports
POST   /api/reports/generate         { report_type, period }
GET    /api/reports/{id}
GET    /api/reports/{id}/download
GET    /api/report-schedules
POST   /api/report-schedules

GET    /api/search?q=                // permission-scoped global search (§47)
GET    /api/audit?entity=&actor=&from=&to=
GET    /api/health                   // scheduler, queues, dead-letter, storage (§55)
GET    /api/integrations
```

---

## 3. Representative request/response shapes

### POST /api/invoices/{id}/payments

```json
// request
{ "amount": 2500.00, "method": "mpesa", "reference": "QK7X…", "payment_date": "2026-09-10" }
// response (201)
{ "payment_id": "…", "invoice_status": "PAID", "receipt_id": "…" }
```

### POST /api/tasks/{id}/verify

```json
// request
{ "verification_note": "confirmed with photo evidence", "outcome": "COMPLETED" }
// response (200)
{ "task_id": "…", "status": "COMPLETED", "completed_at": "…" }
```

### GET /api/dashboard (officer)

```json
{
  "attention": { "overdue": 3, "escalated": 1, "verification_queue": 4 },
  "counters": { "open_tickets": 5, "open_maintenance": 2, "arrears": 3,
                "low_stock": 2, "incidents_open": 1, "renewals_due": 2 },
  "quick_actions": [ "create_task", "record_payment", "report_incident", … ]
}
```

---

## 4. Enforcement

- **Validation schemas** on every write (§41, §42).
- **Workflow guard** on every state transition (§9) — invalid transitions return 409.
- **Permission check** on every read/write (§5) — server-side, 4-level tuple.
- **Audit** on every mutation (§38); **idempotency** on every external webhook (§40).

---

*Next in package: [`information-architecture.md`](information-architecture.md).*
