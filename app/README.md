# ADMIN — reference prototype

A zero-dependency Python 3 prototype of the automation architecture for the Administrative
Officer (Farm & Property Management). It demonstrates the workplan's control cycle:

**PLAN → ASSIGN → EXECUTE → MONITOR → VERIFY → RECORD → REPORT → FOLLOW UP**

## Run

```bash
python3 server.py          # listens on http://0.0.0.0:8000
```

Open `http://localhost:8000/` for the dashboard, or use the JSON API.

> The first run creates `admin.db` (SQLite) and seeds the task templates derived from the
> workplan plus a few sample tenants, invoices, maintenance requests, stock items, assets and
> an incident so the dashboard has realistic data.

## What it does

- **Scheduler** (`ensure_tasks`) materialises recurring work every minute from the 17 task
  templates — daily, weekly (Mon/Wed/Fri), monthly, quarterly and seasonal cadences — exactly as
  the workplan specifies. Event-driven items (tenant matters, procurement, incidents) are created
  on occurrence via the API/UI.
- **Reminders & escalation** (`ensure_reminders`) generate `due` and `overdue` reminders for
  anything not yet completed — the "FOLLOW UP" stage.
- **Task register** with status flow *Pending → In Progress → Completed*, overdue detection, and
  search/filter.
- **Auto reports**: the *Weekly Performance Review* (planned / completed / outstanding / delayed)
  is compiled live from the register — no manual assembly.
- **System of record**: every event is stored in SQLite (the seed of the target database in the
  architecture document).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/summary` | KPI counts + weekly review |
| GET | `/api/tasks?status=&area=&q=` | Filtered task register |
| POST | `/api/tasks` | Create a task `{title, responsible, priority, due_date}` |
| POST | `/api/tasks/<id>/status` | Update status `{status}` |
| GET | `/api/templates` | The recurring task templates |
| GET | `/api/reminders` | Pending reminders |
| GET | `/api/health` | Liveness check |

## Notes

- This is a **throwaway reference spike** for feasibility only — the project is architecture-first.
  The authoritative full architecture is [`../docs/architecture.md`](../docs/architecture.md)
  (production stack: Google Workspace → n8n → custom, plus the roadmap). Implementation proceeds only
  after that architecture is approved.
- Port is fixed at **8000**; bind is `0.0.0.0` so it works behind a preview proxy.
- `admin.db` is git-ignored.
