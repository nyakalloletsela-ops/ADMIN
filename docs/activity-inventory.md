# Activity Inventory & Automation Matrix

> Source: `Administrative_Officer_Farm_Property_Coordination_Workplan.pdf` and
> `Administrative_Officer_Job_Description-1.pdf`.

Every activity is classified against the three questions that determine *how* it should be
automated:

1. **Trigger** — *When* does it happen? (time-based / event-based / threshold-based)
2. **Automation level** — *How much* can a machine do?
   - **FULL** — the system performs the task end-to-end (generate, remind, compile, record).
   - **PARTIAL** — a human performs the task; the system schedules, tracks, reminds, records and escalates.
   - **ASSIST** — a human decides; the system supplies data, checklists, templates and history.
3. **Mechanism** — *What tooling* realises it.

---

## Part A — Coordination of Key Tasks Workplan (14 key areas)

| # | Key area | Key tasks | Frequency | Responsible | Admin Officer role | Performance indicator | Trigger | Level | Proposed automation mechanism |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Farm Operations | Coordinate crop & livestock activities | Daily/Weekly | Farm Supervisor / Caretakers | Plan, coordinate, monitor | Activities completed as scheduled | Time (daily) | PARTIAL | Auto-generated daily checklist for the supervisor; completion is logged and rolled into the daily summary. |
| 2 | Crop Production | Planting, weeding, fertilising, irrigation, harvesting | Seasonal/Weekly | Farm Workers | Maintain schedule & records | Crop activities on time | Time (crop calendar) | PARTIAL | Seasonal crop calendar issues each activity on its due date; records feed the crop history log. |
| 3 | Livestock | Feeding, watering, health checks, stock counts | Daily | Caretakers / Workers | Monitor & verify | Animals cared for; records updated | Time (daily) + threshold | PARTIAL | Daily care checklist + stock-count form auto-update the livestock register; anomalies raise an alert. |
| 4 | Farm Workers | Attendance, duty allocation, supervision | Daily | Supervisor | Monitor attendance & performance | High task-completion rate | Time (daily) | PARTIAL | Attendance captured (WhatsApp/Form) into a rota; duty allocation published; completion stats auto-computed. |
| 5 | Property Management | Inspections & condition monitoring | Weekly/Monthly | Caretakers | Coordinate inspections & reports | Inspection reports completed | Time (weekly) + event | PARTIAL | Scheduled inspection with a mobile checklist; the report auto-files and any defect becomes a maintenance work order. |
| 6 | Accommodation | Occupancy, vacancies, leases, occupant records | Weekly/Monthly | Admin Officer | Maintain portfolio records | Accurate occupancy records | Event (lease lifecycle) | FULL | Lease events (sign, renew, terminate) auto-update the occupancy register; vacancies and expiry dates generate alerts. |
| 7 | Tenant Matters | Complaints, requests, follow-up | As required | Admin Officer / Caretaker | Log, coordinate, escalate | Resolved within agreed time | Event | PARTIAL | Intake form/WhatsApp → ticket with SLA timer → auto-escalation if unresolved. |
| 8 | Maintenance | Repairs, defects, preventative maintenance | Daily/Weekly | Caretakers / Contractors | Log & coordinate work | Jobs tracked to completion | Event + time (PPM) | PARTIAL | Request → work order → contractor assignment → completion sign-off; preventative maintenance on a schedule. |
| 9 | Procurement | Farm/property supplies & services | As required | Admin Officer | Coordinate requests & approvals | Approved purchases documented | Event | PARTIAL | Request → approval workflow → purchase order → goods receipt; budget & spend tracked. |
| 10 | Stock Control | Feed, seed, fertiliser, cleaning materials, supplies | Weekly/Monthly | Responsible Staff | Verify records & stock levels | Minimal unexplained variances | Time + threshold | PARTIAL | Stock-count form → ledger update; reorder alerts at min-level; variance report flags discrepancies. |
| 11 | Assets | Equipment & property asset monitoring | Monthly/Quarterly | Admin Officer | Maintain asset register | Assets accounted for | Time (audit) + event | FULL | Digital asset register with QR labels; scheduled audit reminders; movement/transfer log. |
| 12 | Records | Registers, logs, invoices, supporting documents | Daily/Weekly | Admin Officer | Maintain & file records | Records complete & current | Continuous | FULL | Digitised system of record: every event writes to the right register automatically; documents filed & searchable. |
| 13 | Reporting | Weekly & monthly management reports | Weekly/Monthly | Admin Officer | Compile & submit reports | Reports submitted on time | Time | FULL | Reports auto-compiled from registers and emailed on schedule (Friday weekly, month-end monthly). |
| 14 | Incidents | Loss, damage, illness, theft, accidents, disputes | Immediate | All Staff | Record, escalate, follow up | Incidents reported promptly | Event (immediate) | PARTIAL | One-tap incident report → immediate alert to the escalation matrix → follow-up loop until closed. |

### Daily & weekly coordination routines

| Routine | Content | Trigger | Level | Mechanism |
| --- | --- | --- | --- | --- |
| Daily — Morning | Confirm attendance; review priorities; allocate duties; livestock feeding/health checks; urgent crop/property matters | Time (08:00) | PARTIAL | Morning briefing checklist generated from open tasks; attendance intake opens. |
| Daily — During the day | Monitor progress; coordinate maintenance/contractors; tenant follow-up; record problems/delays/incidents | Continuous | PARTIAL | Live task board; one-tap "log problem/incident". |
| Daily — End of day | Verify completed tasks; identify outstanding work; update logs; confirm evening routines; escalate; daily summary | Time (16:30) | FULL | Auto-compiled end-of-day summary from task status + logs; outstanding items auto-escalated. |
| Weekly — Monday | Review outstanding work; set priorities; allocate responsibilities & deadlines | Time (Mon 08:00) | PARTIAL | Weekly planning board pre-populated with outstanding tasks. |
| Weekly — Tue–Thu | Monitor progress; inspections; maintenance & farm follow-up; resolve issues | Time | PARTIAL | Scheduled mid-week inspection + follow-up reminders. |
| Weekly — Friday | Review completed/outstanding; review performance; update records; weekly report; set next-week priorities | Time (Fri 14:00) | FULL | Weekly review template auto-filled; report generated & sent; next-week priorities captured. |

---

## Part B — Job Description (Property Management focus)

| Group | Activities | Trigger | Level | Mechanism |
| --- | --- | --- | --- | --- |
| Tenant Placement & Administration | Advertise; process applications; vet; recommend; move-in; occupancy register | Event | PARTIAL/ASSIST | Listing → auto-publish; application form → applicant pipeline; scoring sheet supports vetting; move-in checklist updates occupancy register (FULL). |
| Lease Administration | Prepare/administer leases; signing; renewals & terminations; lease database | Event + time | FULL/PARTIAL | Template lease auto-filled from tenant data; e-signature; renewal alerts at −90/−60/−30 days; lease database auto-updated. |
| Rent Collection & Financial Admin | Invoices; payments; arrears; tenant accounts; monthly rent report; deposits/refunds | Time + threshold | FULL | Auto invoice on billing day; payment link + auto receipt; arrears aging + escalation; tenant ledger; auto monthly rent report. |
| Property Maintenance Coordination | Log requests; inspections; contractors; repairs; records | Event + time | PARTIAL | Same pipeline as workplan items 5 & 8. |
| Records Management | Tenant files; filing systems; monthly reports | Continuous | FULL | Document management with per-tenant files; monthly reports auto-generated. |
| Legal & Regulatory Compliance | Lease compliance; notices; documentation; law compliance | Event + time | ASSIST/PARTIAL | Notice templates with auto-date computation; compliance calendar with reminders; document checklist per action. |
| Customer Service | Enquiries; complaints; positive tenant relations | Event | PARTIAL | FAQ chatbot + ticket queue with SLA; complaint escalation. |
| General Administration | Inspections; policy implementation; assigned duties | Mixed | PARTIAL | Shared task board; policy library; delegated tasks tracked. |
| Authority | Verify applications; recommend selection; coordinate leases/maintenance; routine correspondence | Event | ASSIST | Decision-support dashboards; correspondence templates with auto-merge fields. |

---

## Summary by automation level

| Level | Count (of workplan areas) | Meaning for the officer |
| --- | --- | --- |
| FULL | 3 areas (Accommodation, Records, Reporting) + rent billing/reporting | The system *does* the task; the officer reviews & signs off. |
| PARTIAL | 10 areas | The officer *acts*; the system schedules, reminds, tracks, records and escalates. |
| ASSIST | 1 area + decision points (vetting, selection, legal) | The officer *decides*; the system supplies complete, current data. |
