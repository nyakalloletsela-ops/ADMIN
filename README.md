# ADMIN — Administrative Officer Management Platform (Farm & Property)

Architecture-first automation platform for the Administrative Officer's farm & property-management
coordination work, derived from the two source documents:

- `Administrative_Officer_Farm_Property_Coordination_Workplan.pdf`
- `Administrative_Officer_Job_Description-1.pdf`

> **Status: architecture phase.** The authoritative spec is the **Master Build Prompt** (25 domains,
> single system of record, the `PLAN → ASSIGN → EXECUTE → MONITOR → VERIFY → RECORD → REPORT →
> FOLLOW UP` control cycle). No implementation code is written until this architecture is approved.
> PR: [#1](https://github.com/nyakalloletsela-ops/ADMIN/pull/1).

## Architecture package

| Deliverable (§78) | Document |
| --- | --- |
| 1 · Complete system architecture | [`docs/architecture.md`](docs/architecture.md) |
| 2 · Domain map · 3 · Dependency graph | [`docs/domain-map.md`](docs/domain-map.md) |
| 4 · Database ERD · 5 · Entity/data dictionary | [`docs/data-model.md`](docs/data-model.md) |
| 6 · Role–permission matrix | [`docs/role-permission-matrix.md`](docs/role-permission-matrix.md) |
| 7 · Workflow / state-machine definitions | [`docs/workflows.md`](docs/workflows.md) |
| 8 · Event catalogue | [`docs/event-catalogue.md`](docs/event-catalogue.md) |
| 9–11 · Task-template · Scheduler · Notification/Escalation | [`docs/automation-engines.md`](docs/automation-engines.md) |
| 12 · API contract | [`docs/api-contract.md`](docs/api-contract.md) |
| 13 · Navigation/IA · 14 · Dashboard spec | [`docs/information-architecture.md`](docs/information-architecture.md) |
| 15 · Integration architecture | [`docs/integrations.md`](docs/integrations.md) |
| 16 · Security · 17 · Audit architecture | [`docs/security-architecture.md`](docs/security-architecture.md) |
| 18 · Offline / sync architecture | [`docs/offline-sync.md`](docs/offline-sync.md) |
| 19 · Testing strategy | [`docs/testing-strategy.md`](docs/testing-strategy.md) |
| 20 · Phased implementation plan | [`docs/implementation-plan.md`](docs/implementation-plan.md) |
| — · Requirements & automation matrix | [`docs/activity-inventory.md`](docs/activity-inventory.md) |
| — · PROVEN / INFERRED / DECISION_REQUIRED | [`docs/assumptions.md`](docs/assumptions.md) |

## Reference spike (not part of the architecture phase)

| Path | What it is |
| --- | --- |
| [`app/`](app/README.md) | Zero-dependency Python 3 feasibility spike (scheduler + task register). Throwaway — to be rebuilt per the approved architecture. |

## How to read

1. Start with [`docs/architecture.md`](docs/architecture.md) **§1–§8** (why & what).
2. Review the package documents for the technical design (data, workflows, engines, security).
3. Read [`docs/implementation-plan.md`](docs/implementation-plan.md) for the build order, and
   [`docs/assumptions.md`](docs/assumptions.md) for the `DECISION_REQUIRED` items that gate specific
   phases.
