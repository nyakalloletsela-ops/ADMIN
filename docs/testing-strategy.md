# Testing Strategy
## Architecture package — item 19

> Master document: [`architecture.md`](architecture.md). A feature is "complete" only when its
> UI + API + domain logic + database + validation + authorization + workflow + audit + tests are all
> connected (§79). Screens alone do not count.

---

## 1. Test pyramid & responsibilities

| Layer | Scope | Tools (Option B/C) |
| --- | --- | --- |
| Unit | business rules, calculations, validation | pytest / vitest |
| Integration | cross-domain workflows, repository+service | pytest + test DB |
| Workflow | every state transition (valid + invalid) | state-machine test harness |
| Permission | unauthorised access is denied server-side | RBAC test matrix |
| Automation | scheduler, reminders, escalation, events, idempotency | fake clock, event test doubles |
| Data integrity | duplicates, FKs, financial immutability, audit | DB constraint tests |
| End-to-end | UI-driven happy paths | Playwright |

## 2. Required test suites

### 2.1 Unit tests (business rules)

- Arrears computation & aging buckets (`CURRENT/1–30/31–60/61–90/90+`).
- Stock variance & reorder threshold logic.
- SLA countdown & breach detection.
- Report aggregation (no fake numbers — computed from fixtures).
- Notification template merge fields.
- Currency/amount handling (2-dp, no float drift).

### 2.2 Integration tests (cross-domain workflows)

- `Application → Approval → Lease → Invoice → Payment` (§73 end-to-end requirement).
- `Maintenance Request → Work Order → Completion → Verification → Closure`.
- `Stock Count → Variance → Investigation`.
- `Task Template → Scheduled Task → Reminder → Completion → Verification`.
- `Inspection → Finding → Defect → Maintenance Request → Work Order`.
- `Payment → Invoice balance → Tenant ledger → Receipt → Dashboard → Report`.

### 2.3 Workflow tests

- Every valid transition succeeds; every invalid transition is rejected (e.g.
  `IN_PROGRESS → CLOSED` on maintenance must fail).
- Transition guards (evidence/approval/verification required) block when unmet.
- Actor guards: only the right role can `approve`/`verify`/`close`.

### 2.4 Permission tests (RBAC matrix)

- For each role in [`role-permission-matrix.md`](role-permission-matrix.md): allowed actions succeed;
  forbidden actions return 403 and are audited.
- Record-scope: caretaker cannot see another caretaker's tasks; tenant sees only own records.
- Field redaction: sensitive fields absent from unprivileged responses/exports.

### 2.5 Automation tests

- Scheduler materialises each cadence on the right date (fake clock, Africa/Maseru).
- **Idempotency:** re-running a scheduler sweep produces no duplicate tasks/notifications.
- Reminder ladder fires at D−1/D0/D+1/D+2/D+5.
- Escalation matrix fires at configured thresholds (arrears 30/60/90; lease −90/−60/−30).
- Event dedup: replaying `payment.received` with the same key creates one payment.
- Dead-letter: a failing event is retried then surfaced, never silently dropped.

### 2.6 Data integrity tests

- FK violations rejected; uniqueness (`occurrence_key`, `payment.reference`, `idempotency_key`)
  enforced.
- PAYMENT/AUDIT append-only: update/delete paths absent.
- Reversal pattern: original + reversal + corrected; ledger always reconciles.
- Soft-delete present; permanent purge requires privileged role and is audited.

### 2.7 End-to-end tests (minimum, §73)

1. Application → Approval → Lease → Invoice → Payment (tenancy value chain).
2. Maintenance Request → Work Order → Completion → Verification → Closure.
3. Stock Count → Variance → Investigation.
4. Task Template → Scheduled Task → Reminder → Completion → Verification.
5. Offline capture → sync → server state (see [`offline-sync.md`](offline-sync.md) §4).

---

## 3. Acceptance criteria mapping (§74)

| Criterion | Proved by |
| --- | --- |
| A. No orphan tasks | integrity + UI invariant: every active task has owner+deadline+status |
| B. Recurring work automatic | automation tests (scheduler/templates) |
| C. Workflows enforced | workflow tests |
| D. Records update automatically | integration tests (event → register) |
| E. Human approval stays human | permission/workflow tests (no auto-approve path) |
| F. Automation observable | automation audit tests + system health |
| G. Audit exists | data-integrity tests (audit rows on mutations) |
| H. Reports derive from real data | unit/integration report tests |
| I. Permissions work | permission tests |
| J. Cross-domain relationships work | integration tests |

## 4. Quality gates

- CI runs unit + workflow + permission + data-integrity on every change.
- Integration + E2E run on merge to the delivery branch.
- A feature PR is blocked unless its domain's test suites pass and coverage of business rules is
  ≥ 80% (target).

---

*Next in package: [`implementation-plan.md`](implementation-plan.md).*
