# ADMIN — Automation Architecture for the Administrative Officer (Farm & Property Management)

This repository turns the Administrative Officer's paper workplan and job description into an
**automation architecture**: a blueprint for automating the coordination, scheduling, tracking,
reporting and follow-up of every key task — plus a runnable reference prototype.

## What's inside

| Path | What it is |
| --- | --- |
| [`docs/activity-inventory.md`](docs/activity-inventory.md) | Every activity from the workplan & job description, normalised into an automation matrix (frequency → trigger → automation level → mechanism). |
| [`docs/automation-architecture.md`](docs/automation-architecture.md) | The full architecture: target system design, data model, scheduling & triggers, notifications/escalation, technology options, roadmap, KPIs and risks. |
| [`app/`](app/README.md) | A zero-dependency Python reference prototype (scheduler + task register + dashboard + API) that demonstrates the **PLAN → ASSIGN → EXECUTE → MONITOR → VERIFY → RECORD → REPORT → FOLLOW UP** control cycle. |

## Source documents

- `Administrative_Officer_Farm_Property_Coordination_Workplan.pdf`
- `Administrative_Officer_Job_Description-1.pdf`

## Quick start (prototype)

The prototype needs only Python 3 (no external packages):

```bash
cd app
python3 server.py          # starts on http://0.0.0.0:8000
```

Then open the dashboard at `/` (or the live preview), or hit the JSON API at `/api/summary`,
`/api/tasks`, etc. See [`app/README.md`](app/README.md) for details.
