# Role–Permission Matrix
## Architecture package — item 6

> Master document: [`architecture.md`](architecture.md). Authorisation is **server-side enforced**;
> the UI only reflects it (§5 — "Never rely solely on frontend hiding").

---

## 1. Roles

| Role | Scope | Purpose |
| --- | --- | --- |
| **System Administrator** | Full system | Platform configuration, users, integrations, all data |
| **Administrative Officer** | Operational | Day-to-day coordination & CRUD authority across operations |
| **Head of Support Services** | Management oversight | Approvals, escalation authority, oversight dashboards |
| **Caretaker Supervisor** | Team coordination | Property/farm team coordination, verification |
| **Caretaker** | Assigned tasks | Own operational tasks only |
| **Farm Worker** | Farm activities | Assigned farm activities + attendance/duties |
| **Contractor** | Assigned work | Own maintenance/procurement work only |
| **Tenant** | Own tenancy | Own requests, notices, payments, documents |
| **Management** | Read + approvals | Read-only management info + permitted approvals |

## 2. Permission model (§5)

Permissions are a 4-level tuple — **Module → Action → Record → Field**:

- **Action vocabulary:** `view, create, edit, delete, approve, reject, assign, verify, close, export,
  upload, download, escalate`.
- **Record scope:** `all / team / assigned / own / none`.
- **Field scope:** field-level redaction for sensitive columns (e.g. tenant `id_number`).

---

## 3. Module × Role action matrix

Legend: **C** = create · **R** = read/view · **U** = update/edit · **D** = delete (soft/privileged) ·
**A** = approve · **J** = reject · **G** = assign · **V** = verify · **X** = close · **E** = escalate ·
**Ex** = export · **Up** = upload · **Dl** = download.

| Module | SysAdmin | Admin Officer | HoSS | Caret. Sup. | Caretaker | Farm Worker | Contractor | Tenant | Mgmt |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| Users / Roles / Permissions | CRUD | — | — | — | — | — | — | — | — |
| Task Templates | CRUD | CRU | R | R | — | — | — | — | R |
| Tasks | CRUD | CRUD+GVX+E | R+E | R+G+V (team) | RU (assigned) | RU (assigned) | RU (assigned) | — | R |
| Properties / Units | CRUD | CRUD | R | R | R | — | — | — | R |
| Applications | R | CRUD+A/J | A/J | R | — | — | — | — | R |
| Tenants (360°) | CRUD | CRUD | R | R | limited R | — | — | own R+U(contact) | R |
| Leases | CRUD | CRUD+renew | A (renew/term) | R | — | — | — | own R | R |
| Invoices / Payments | CRUD | CRU+Dl | R+A (refunds) | — | — | — | — | own R+pay | R |
| Deposits / Refunds | CRUD | CRU | A | — | — | — | — | own R | R |
| Maintenance Requests / Work Orders | CRUD | CRUD+GVX | R | R+G+V | RU (assigned) | — | RU (assigned) | own C+R | R |
| Inspections | CRUD | CRUD+V | R | R+U+V | RU (assigned) | — | — | — | R |
| Tickets (Service Desk) | CRUD | CRUD+GVX+E | R+E | R | — | — | — | own C+R | R |
| Farm Operations (view) | CRUD | CRUD | R | R | — | — | — | — | R |
| Crop Plans / Activities | CRUD | CRUD+V | R | R | RU (assigned) | RU (assigned) | — | — | R |
| Livestock Records | CRUD | CRUD+V | R | R | RU (assigned) | RU (assigned) | — | — | R |
| Workforce / Attendance / Duties | CRUD | CRUD+V | R | R+V | — | own R+U | — | — | R |
| Stock Items / Movements / Counts | CRUD | CRUD+V | R | R | RU (count entry) | — | — | — | R |
| Stock Adjustments | CRUD | RU (needs A) | A | — | — | — | — | — | R |
| Assets / Asset Audits | CRUD | CRUD+V | R | R | RU (assigned) | — | — | — | R |
| Procurement (Request→Order→Receipt) | CRUD | C+R+U; A/J (per threshold) | A/J (per threshold) | C (team) | — | — | — | — | R |
| Incidents | CRUD | CRUD+GVX+E | R+E | C+U | C | C | — | C | R |
| Compliance Obligations | CRUD | CRU | R+A | R | — | — | — | — | R |
| Documents | CRUD+Dl | CRU+Up+Dl | R+Dl | R+Up (assigned) | Up (own evidence) | Up (own evidence) | Up (own work) | Up (own)+Dl(own) | R+Dl |
| Reports | CRUD+Ex | R+Ex | R+Ex | limited R | — | — | — | — | R+Ex |
| Calendar | CRUD | CRUD | R | R | own R | own R | own R | — | R |
| Notifications (centre) | CRUD | CRUD | R | own | own | own | own | own | own |
| Escalation Rules | CRUD | CRU | R | — | — | — | — | — | R |
| Administration settings | CRUD | CRU (some) | R | — | — | — | — | — | R |
| Audit Log | R | R | R | — | — | — | — | — | R |
| System Health | CRUD | R | R | — | — | — | — | — | R |
| Integrations | CRUD | R | R | — | — | — | — | — | R |

---

## 4. Record-scope rules (examples)

| Role | Record scope |
| --- | --- |
| Caretaker / Farm Worker / Contractor | `assigned` only — see nothing else |
| Caretaker Supervisor | `team` for team tasks, inspections, attendance verification |
| Tenant | `own` tenancy, leases, invoices, tickets, documents, communications |
| HoSS / Management | `all` read + specific approvals |

## 5. Field-level redaction (examples)

| Field | Visible to |
| --- | --- |
| Tenant `id_number` | Admin Officer, HoSS, SysAdmin (not caretakers, not management export) |
| Payment `reference` | Rent domain staff only |
| Vetting notes | Admin Officer, HoSS |
| Audit `before/after` payload | SysAdmin, Admin Officer, HoSS (read-only) |

## 6. Enforcement

1. Every API call resolves the caller's roles → checks the 4-level permission tuple **server-side**.
2. Denials are logged as `403` events in `AUDIT_LOG` (detects probing).
3. UI renders actions/columns from the same permission service (single source of truth).
4. **No auto-approvals** anywhere; `approve/reject` are always user actions (§53).

---

*Next in package: [`workflows.md`](workflows.md).*
