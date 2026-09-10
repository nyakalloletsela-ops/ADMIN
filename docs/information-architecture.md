# Information Architecture & Dashboard Specification
## Architecture package — items 13 & 14

> Master document: [`architecture.md`](architecture.md). The UI is **operational, not decorative**
> (§49). It exists to answer: *what needs attention, who owns it, when is it due, why is it late,
> what action is required, what evidence exists, what happens next.*

---

## 1. Navigation / information architecture

Desktop-first for officer/admin; mobile-friendly for field workers (§57). Role-scoped navigation:
items appear only if the role can view the module.

### 1.1 Global navigation (officer, grouped)

```text
ADMIN PLATFORM
├── Dashboard
├── Work
│   ├── Tasks & Workplan
│   ├── Calendar & Scheduling
│   └── My Notifications
├── Property
│   ├── Properties & Units
│   ├── Tenants & Applications
│   ├── Leases
│   ├── Rent & Finance
│   ├── Maintenance
│   ├── Inspections
│   └── Tenant Service Desk
├── Farm
│   ├── Farm Operations (control centre)
│   ├── Crop Production
│   ├── Livestock
│   └── Workforce & Attendance
├── Logistics
│   ├── Stock Control
│   ├── Assets
│   └── Procurement
├── Governance
│   ├── Incidents
│   ├── Compliance
│   ├── Records & Documents
│   └── Communications
├── Reports & Analytics
└── Administration (admin only)
    ├── Users, Roles & Permissions
    ├── Task Templates & Workflows
    ├── SLA / Escalation / Notification rules
    ├── Categories & Settings
    ├── Integrations
    ├── Audit Log
    └── System Health
```

### 1.2 Role-simplified menus

| Role | Menu |
| --- | --- |
| Caretaker / Farm Worker | Today's duties → Start → Complete → Evidence → Submit (mobile-first) |
| Caretaker Supervisor | Team tasks, Inspections, Verification queue, Team attendance |
| Contractor | Assigned work orders, Documents, Communications |
| Tenant | My tenancy: lease, invoices/payments, requests, notices, documents |
| Management / HoSS | Dashboard, Reports, Approvals queue, Read-only views |

### 1.3 Global elements

- **Global search** (§47): searches all permitted entities; results respect permissions.
- **Notification bell** with unread/urgent/overdue/escalated sections (§35).
- **Quick actions** (see §3) always reachable.
- **Help / context** and **system status** link in the footer.

---

## 2. Detail-page structure (§60)

Every important record follows one consistent layout:

```text
Header        : title + identifier + status pill + primary actions
Summary       : key facts strip (owner, dates, amounts, location)
Status        : current workflow state + next allowed transition buttons
Key info      : full field set, grouped
Related       : linked records (tenant→lease→invoices→tickets→documents)
Documents     : evidence & files (permission-scoped)
Timeline      : chronological activity (from events, §48)
Audit         : mutation history (permission-scoped)
```

---

## 3. Quick actions (§50)

Always available to the officer (permission-gated), each opening a focused dialog that persists to
the real data model:

`create task · assign task · record payment · add tenant · create lease · report maintenance ·
create work order · record stock count · report incident · schedule inspection · create procurement
request · upload document`

---

## 4. Dashboard specification (§12, §49)

Dashboards are **role-resolved** and derived from authoritative data — no fake metrics, no decorative
cards, no huge empty grids. Layout: **attention-first**.

### 4.1 Administrative Officer dashboard

| Section | Contents | Drives |
| --- | --- | --- |
| **Attention** | overdue, escalated, verification queue (top, red/amber) | Tasks |
| **Today** | due-today tasks with owner + time | Scheduler |
| **Tenants & rent** | arrears by bucket, renewals due (90/60/30), vacancies | Rent, Lease |
| **Operations** | open tickets, open maintenance, upcoming inspections | Service desk, Maintenance |
| **Farm** | today's crop/livestock/attendance status | Farm |
| **Logistics** | low stock, variances, procurement awaiting approval, asset flags | Stock, Assets, Procurement |
| **Incidents** | open incidents by severity | Incidents |
| **Deadlines** | upcoming compliance/report/audit dates | Calendar |
| **Notification queue** | unread/urgent/escalated | Notifications |

### 4.2 Management dashboard

| Section | Contents |
| --- | --- |
| Portfolio | occupancy rate, vacancies, unit status |
| Rent | collection %, arrears aging trend, deposits held |
| Operations | maintenance backlog, work-order cycle time, inspection completion |
| Work | task completion rate, overdue trend, escalation count |
| Farm | activity completion, livestock counts, attendance rate |
| Logistics | stock variance trend, procurement spend, asset audit status |
| Incidents | count by severity, time-to-resolve |
| Trends | month-over-month KPI charts (from Reports) |

### 4.3 Dashboard rules

- Every number links to its source list (click-through, no dead metrics).
- "Attention" items are actionable (deep-link + action buttons).
- Empty states show guidance ("No overdue tasks — nothing needs escalation today").
- Refresh is live/polled; nothing requires manual export to view.

---

## 5. Lists, forms & mobile (§57–61)

- **Tables:** search, filter, sort, pagination, column selection, export (where permitted).
- **Forms:** immediate validation, required markers, preserve input on recoverable error, attachments,
  related-record context, step-wise for long workflows (never one giant form).
- **Destructive actions:** confirmation required; deletes are soft/privileged (§68).
- **Field experience (mobile):** large targets, minimal typing, photo evidence, and a visible sync
  state — `ONLINE · OFFLINE · SYNCING · SYNCED · SYNC ERROR` (§61). Never pretend a record synced when
  it has not.

---

## 6. Design system

- **States:** loading, empty, error, success for every view.
- **Components:** consistent tables, status pills, dialogs, drawers, date/time pickers, attachment
  uploader, workflow transition buttons, timeline, audit viewer.
- **Accessibility & bandwidth:** semantic HTML, keyboard navigable, low-bandwidth conscious assets,
  readable typography (§57).

---

*Next in package: [`integrations.md`](integrations.md).*
