# Workflow & State-Machine Definitions
## Architecture package — item 7

> Master document: [`architecture.md`](architecture.md). Every transition carries: **actor**,
> **condition**, **required evidence**, **approval requirement**, **notifications**, and an
> **audit event**. Workflows are enforced server-side (§9) — the UI cannot jump states.

---

## 1. Task lifecycle (Task Engine)

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> ASSIGNED : assign
    PENDING --> CANCELLED : cancel (reason)
    ASSIGNED --> IN_PROGRESS : start
    ASSIGNED --> CANCELLED : cancel (reason)
    IN_PROGRESS --> BLOCKED : block (reason)
    BLOCKED --> IN_PROGRESS : unblock
    IN_PROGRESS --> SUBMITTED : submit
    SUBMITTED --> VERIFICATION_REQUIRED : verification_required
    SUBMITTED --> COMPLETED : no verification needed
    VERIFICATION_REQUIRED --> COMPLETED : verify
    VERIFICATION_REQUIRED --> REJECTED : reject (reason)
    SUBMITTED --> REJECTED : reject (reason)
    IN_PROGRESS --> ESCALATED : overdue/escalation rule
    ASSIGNED --> ESCALATED : overdue/escalation rule
    PENDING --> ESCALATED : overdue/escalation rule
    ESCALATED --> ASSIGNED : reassign
    ESCALATED --> IN_PROGRESS : resume
    COMPLETED --> [*]
    REJECTED --> [*]
    CANCELLED --> [*]
```

| Transition | Actor | Condition | Evidence | Notifications | Audit |
| --- | --- | --- | --- | --- | --- |
| assign | officer/supervisor | PENDING | — | assignee | yes |
| start | assignee | ASSIGNED | — | owner | yes |
| block/unblock | assignee | IN_PROGRESS | reason | owner | yes |
| submit | assignee | IN_PROGRESS | required if `evidence_required` | verifier | yes |
| verify | verifier | VERIFICATION_REQUIRED | verifier sign-off | owner | yes |
| reject | verifier | SUBMITTED/VERIFICATION_REQUIRED | reason | assignee | yes |
| complete | system/verifier | SUBMITTED (no verification) | — | owner | yes |
| escalate | rules engine | overdue/SLA breach | — | ladder (§11) | yes |
| cancel | officer | any active | reason | owner | yes |

> Transition rules come from [`automation-engines.md`](automation-engines.md) §1.

---

## 2. Tenant application (§15)

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> SCREENING : triage
    SCREENING --> VETTING : complete
    SCREENING --> REJECTED : incomplete
    VETTING --> RECOMMENDED : officer recommends
    VETTING --> REJECTED : not suitable
    RECOMMENDED --> APPROVAL : submit for decision
    APPROVAL --> APPROVED : approve
    APPROVAL --> REJECTED : reject
    APPROVED --> OFFER : make offer
    OFFER --> ACCEPTED : tenant accepts
    OFFER --> DECLINED : tenant declines
    ACCEPTED --> MOVE_IN : move-in complete
    MOVE_IN --> [*]
    REJECTED --> [*]
    DECLINED --> [*]
```

- **Approval is human** (§53): `RECOMMENDED → APPROVAL` requires HoSS/officer per config; never automatic.
- **Evidence:** application documents at RECEIVED; vetting checklist at VETTING; decision note at APPROVAL; signed lease at MOVE_IN.

## 3. Lease lifecycle (§17)

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> REVIEW : submit
    REVIEW --> SIGNATURE_PENDING : approve draft
    REVIEW --> DRAFT : amend
    SIGNATURE_PENDING --> SIGNED : signed (e-signature)
    SIGNED --> ACTIVE : start date reached
    ACTIVE --> EXPIRING : -90d
    EXPIRING --> RENEWED : renewal signed
    EXPIRING --> TERMINATING : notice
    ACTIVE --> TERMINATING : notice
    TERMINATING --> CLOSED : move-out complete
    RENEWED --> ACTIVE
    CLOSED --> ARCHIVED : archive
    ARCHIVED --> [*]
```

- Renewal alerts at **−90 / −60 / −30 days**; **never auto-renew** (§17).
- Evidence: signed document (SIGNED), move-out inspection (CLOSED).

## 4. Rent invoice & arrears (§18–19)

```mermaid
stateDiagram-v2
    [*] --> ISSUED
    ISSUED --> PAID : full payment
    ISSUED --> PARTIALLY_PAID : partial payment
    PARTIALLY_PAID --> PAID : balance settled
    ISSUED --> OVERDUE : due date passed
    PARTIALLY_PAID --> OVERDUE : due date passed
    OVERDUE --> PAID : settled (incl. arrangement)
    OVERDUE --> NOTICE_30 : +30d reminder
    NOTICE_30 --> NOTICE_60 : +60d formal notice
    NOTICE_60 --> LEGAL_REFERRAL : +90d (human decision)
    ISSUED --> CANCELLED : reverse (reason)
```

- **Arrears engine** computes outstanding, days overdue, and aging bucket
  (`CURRENT, 1–30, 31–60, 61–90, 90+`) live from the ledger.
- **Legal referral is a human decision** — the system prepares the notice, never sends legal action
  itself (§19, §53).
- Payments are append-only; corrections are reversal/adjustment entries (§38).

## 5. Maintenance (§20)

```mermaid
stateDiagram-v2
    [*] --> REPORTED
    REPORTED --> TRIAGED : classify + priority + SLA
    TRIAGED --> ASSIGNED : contractor + quote
    TRIAGED --> CANCELLED : duplicate / not needed
    ASSIGNED --> IN_PROGRESS : work starts
    IN_PROGRESS --> COMPLETED : done + evidence
    COMPLETED --> VERIFIED : verify (officer/supervisor)
    VERIFIED --> CLOSED : close
    COMPLETED --> IN_PROGRESS : rework (reject verification)
```

- Source may be a **ticket**, an **inspection defect**, or direct report (§52).

## 6. Inspection → defect chain (§21)

```mermaid
stateDiagram-v2
    [*] --> SCHEDULED
    SCHEDULED --> IN_PROGRESS : start
    IN_PROGRESS --> REPORT_FILED : checklist + photos
    REPORT_FILED --> CLOSED : no findings
    REPORT_FILED --> DEFECT_LOGGED : findings present
    DEFECT_LOGGED --> MAINTENANCE_REQUEST : auto-spawn
    MAINTENANCE_REQUEST --> [*]
    REPORT_FILED --> CLOSED
    CLOSED --> [*]
```

## 7. Stock count & variance (§26)

```mermaid
stateDiagram-v2
    [*] --> SCHEDULED
    SCHEDULED --> IN_PROGRESS : start count
    IN_PROGRESS --> SUBMITTED : submit counts
    SUBMITTED --> RECONCILIATION : compare vs ledger
    RECONCILIATION --> CLOSED : no variance
    RECONCILIATION --> VARIANCE_REVIEW : variance > 0
    VARIANCE_REVIEW --> INVESTIGATION : variance > threshold
    VARIANCE_REVIEW --> ADJUSTED : authorised adjustment
    INVESTIGATION --> ADJUSTED : resolution approved
    ADJUSTED --> CLOSED
    CLOSED --> [*]
```

- **Never silently alter balances** (§26): adjustments require approval; variances above threshold
  spawn an investigation task.

## 8. Procurement (§28)

```mermaid
stateDiagram-v2
    [*] --> REQUESTED
    REQUESTED --> REVIEW : validate + cost
    REVIEW --> APPROVAL : submit
    REVIEW --> REJECTED : not valid
    APPROVAL --> APPROVED : approve (per threshold)
    APPROVAL --> REJECTED : reject
    APPROVED --> PURCHASE_ORDER : issue PO
    PURCHASE_ORDER --> ORDERED : order placed
    ORDERED --> RECEIVED : goods received
    RECEIVED --> VERIFIED : verify qty/condition
    VERIFIED --> RECORDED : stock receipt / asset created
    RECORDED --> [*]
    REJECTED --> [*]
```

- Approval authority is **configurable** — `DECISION_REQUIRED: procurement approval thresholds`
  ([`assumptions.md`](assumptions.md)). Never auto-approve purchases (§28, §53).

## 9. Incident management (§29)

```mermaid
stateDiagram-v2
    [*] --> REPORTED
    REPORTED --> ACKNOWLEDGED : auto-ack + notify
    ACKNOWLEDGED --> ASSIGNED : assign owner
    ASSIGNED --> INVESTIGATING : start
    INVESTIGATING --> RESOLVING : corrective action
    RESOLVING --> RESOLVED : resolved
    RESOLVED --> VERIFIED : verify
    VERIFIED --> CLOSED : close
    ACKNOWLEDGED --> ESCALATED : CRITICAL / unresolved
    ESCALATED --> ASSIGNED : authority action
    CLOSED --> [*]
```

- Severity `LOW/MEDIUM/HIGH/CRITICAL`; **CRITICAL triggers immediate notification** to officer + HoSS
  (§29). Incidents never enter normal task queues silently.

## 10. Tenant service desk (§30)

```mermaid
stateDiagram-v2
    [*] --> OPEN
    OPEN --> ACKNOWLEDGED : officer ack
    ACKNOWLEDGED --> IN_PROGRESS : work starts
    IN_PROGRESS --> WAITING : awaiting tenant/contractor
    WAITING --> IN_PROGRESS : resume
    IN_PROGRESS --> RESOLVED : resolved
    RESOLVED --> CLOSED : tenant confirms / timeout
    OPEN --> ESCALATED : SLA breach
    ACKNOWLEDGED --> ESCALATED : SLA breach
    ESCALATED --> IN_PROGRESS : reassigned
```

## 11. Workflow engine contract (§9)

Every workflow definition is data (configurable), not code:

```text
WORKFLOW = {
  entity, states[], transitions[],
  transition = { from, to, actor_role, condition, evidence_required, approval_required,
                 notify[], audit_event }
}
```

- Enforced by a single reusable **state-machine validator** used by all domains.
- Any invalid transition returns a domain error ("cannot transition IN_PROGRESS → CLOSED") and is
  logged — never silently ignored.

---

*Next in package: [`event-catalogue.md`](event-catalogue.md).*
