# ADMIN — Automation of the Administrative Officer (Farm & Property Management)

This repository holds the **architecture-first** design for automating the Administrative Officer's
farm & property-management coordination work, derived from:

- `Administrative_Officer_Farm_Property_Coordination_Workplan.pdf`
- `Administrative_Officer_Job_Description-1.pdf`

> **Status:** architecture phase — no implementation is committed until the architecture is approved.
> The `app/` prototype is a throwaway feasibility spike, retained for reference only.

## Documents

| Path | What it is |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | **The full architecture** (pre-code): context, requirements, principles, logical & deployment views, data model & dictionary, state machines, scheduling, notifications & escalation, reporting, integrations, security, ADRs, roadmap, costs, risks, KPIs and traceability. |
| [`docs/activity-inventory.md`](docs/activity-inventory.md) | Requirements & automation matrix — every activity from both source PDFs classified by trigger → automation level → mechanism. |

## Reference spike (not part of the architecture phase)

| Path | What it is |
| --- | --- |
| [`app/`](app/README.md) | A zero-dependency Python 3 prototype demonstrating the PLAN → ASSIGN → EXECUTE → MONITOR → VERIFY → RECORD → REPORT → FOLLOW UP cycle. Superseded by the approved architecture; rebuilt properly during implementation phases. |

## How to read

1. Start with **§1–§8** of [`docs/architecture.md`](docs/architecture.md) for the "why and what".
2. Review **§9–§19** for the technical design (views, data, workflows, security).
3. Review **§20–§27** for decisions, roadmap, costs, risks, KPIs and the **open questions** that need
   answers before implementation begins.
