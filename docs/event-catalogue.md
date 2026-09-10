# Event Catalogue
## Architecture package — item 8

> Master document: [`architecture.md`](architecture.md). Events are the only sanctioned way for one
> domain to trigger action in another (§40, §65). All events are **idempotent** and carry a
> correlation ID + idempotency key.

---

## 1. Event envelope (standard contract)

```json
{
  "event_id": "uuid",              // idempotency key (client-generated for inbound)
  "name": "lease.signed",
  "occurred_at": "2026-09-10T08:30:00+02:00",
  "source": "lease-service",
  "correlation_id": "uuid",        // ties the whole chain together
  "actor": { "id": "user-uuid", "type": "user|system|scheduler" },
  "entity": { "type": "LEASE", "id": "lease-uuid" },
  "payload": { }                   // versioned schema per event
}
```

Rules:
- **Idempotent:** consumers deduplicate on `event_id`.
- **Versioned:** `payload` has a schema version; consumers reject unknown versions.
- **Retryable:** failed handling goes to a retry queue, then dead-letter — never silently dropped.
- **Auditable:** every event persists to `SYSTEM_EVENT` and is traceable end-to-end (§66, §69).

---

## 2. Event catalogue

### Tenancy & lease

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `tenant.application.created` | application submitted | officer dashboard, task engine (vetting task) |
| `tenant.application.vetted` | vetting completed | officer, HoSS |
| `tenant.application.approved` | application approved | lease domain (draft lease) |
| `tenant.application.rejected` | application rejected | applicant notification |
| `tenant.created` | tenant record created | records, search index |
| `lease.drafted` | lease in DRAFT | officer |
| `lease.signature_requested` | lease sent for signing | e-signature adapter |
| `lease.signed` | lease fully signed | occupancy, scheduler (renewal watch), rent (invoice setup) |
| `lease.activated` | lease → ACTIVE | occupancy, dashboard |
| `lease.expiring` | −90/−60/−30 d | renewal task, tenant notice, officer alert |
| `lease.renewed` | renewal signed | occupancy, scheduler |
| `lease.terminated` | lease → TERMINATING/CLOSED | rent (final invoice), move-out inspection |
| `occupancy.changed` | unit occupancy status changed | properties dashboard |

### Rent & finance

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `invoice.created` | invoice issued | tenant notification, arrears engine |
| `invoice.overdue` | invoice past due | arrears engine, reminder ladder |
| `payment.received` | payment recorded | ledger, receipt, dashboard, report |
| `payment.reversed` | reversal/adjustment | ledger, audit |
| `rent.arrears.threshold_reached` | 30/60/90 d | notice generation (30/60), legal referral draft (90) |
| `deposit.held` / `deposit.refunded` | deposit lifecycle | ledger, tenant |
| `refund.approved` | refund approved | finance export |

### Maintenance & inspection

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `ticket.created` | tenant request received | service desk, task engine |
| `maintenance.request.created` | request logged | task engine, contractor dispatch |
| `work_order.assigned` | contractor assigned | contractor notification |
| `work_order.completed` | work done + evidence | verification queue |
| `work_order.verified` | verification passed | maintenance history, report |
| `inspection.scheduled` | inspection created | calendar, assignee |
| `inspection.completed` | report filed | defect engine (spawn requests) |
| `defect.discovered` | defect logged | maintenance request (auto-spawn) |

### Tasks & automation

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `task.created` | any task materialised | assignee, dashboard |
| `task.assigned` | task assigned | assignee notification |
| `task.due_soon` | D−1 | reminder ladder |
| `task.overdue` | D+1 | reminder ladder, escalation engine |
| `task.escalated` | ladder escalation (D+2/D+5) | officer/HoSS |
| `task.submitted` | work submitted | verifier |
| `task.verified` | verification passed | owner, report |
| `task.completed` | completed | report, dashboard |
| `task.rejected` | verification rejected | assignee |
| `task.blocked` / `task.unblocked` | blocked state | owner |

### Farm

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `crop.plan.created` | season plan created | scheduler (crop activities) |
| `crop.activity.due` | activity window reached | task engine |
| `crop.activity.completed` | activity done + verified | crop history |
| `livestock.check.completed` | daily care recorded | dashboard |
| `livestock.anomaly.detected` | count/health anomaly | incident (auto-draft) |
| `attendance.submitted` | attendance captured | supervisor verify, export |
| `duty.allocated` | duty assigned | worker notification |

### Stock, assets, procurement

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `stock.count.submitted` | count submitted | reconciliation |
| `stock.variance.detected` | variance found | investigation task, officer alert |
| `stock.reorder.triggered` | qty ≤ reorder level | procurement request draft |
| `stock.adjusted` | authorised adjustment | ledger, audit |
| `asset.audit.completed` | audit done | asset register |
| `asset.missing.detected` | asset not found | investigation task + alert |
| `procurement.request.created` | request created | approval queue |
| `procurement.approved` | request approved | PO issuance |
| `purchase_order.issued` | PO issued | supplier |
| `purchase_order.received` | goods received | stock receipt / asset creation |

### Incidents, compliance, service

| Event | Emitted when | Primary consumers |
| --- | --- | --- |
| `incident.reported` | incident logged | severity assessment |
| `incident.critical` | CRITICAL severity | immediate notification (officer + HoSS) |
| `incident.escalated` | escalation | authority |
| `incident.resolved` | resolved | report |
| `compliance.obligation.due` | obligation due | reminder, task |
| `document.uploaded` | document filed | records, linked entity timeline |
| `report.generated` | report compiled | archive, notification |
| `system.job.failed` | any automation failure | system health (§55) |

---

## 3. Event → automation mapping (examples, §52)

| Trigger event | Automatic chain |
| --- | --- |
| `lease.expiring` | → renewal task → tenant notification → officer dashboard alert |
| `defect.discovered` | → maintenance request → work order → task → SLA → contractor → verification → history |
| `stock.reorder.triggered` | → procurement request **draft** → officer approval (never auto-buy) |
| `payment.received` | → payment record → invoice balance → tenant ledger → receipt → dashboard → report |
| `incident.critical` | → severity assessment → immediate notification → task → escalation → resolution → report |

---

## 4. Inbound external events (idempotency)

| Source | Event | Idempotency key |
| --- | --- | --- |
| WhatsApp webhook | `inbound.message` | Twilio `MessageSid` |
| Mobile-money webhook | `payment.confirmation` | provider `trans_id` |
| E-signature webhook | `lease.signed.external` | envelope `id` + `status` |
| Email inbound | `inbound.email` | `message_id` |

Each inbound event is validated, keyed, deduplicated, then translated into a domain event
(`payment.received`, `lease.signed`, etc.) with the provider key preserved in `correlation_id`.

---

*Next in package: [`automation-engines.md`](automation-engines.md).*
