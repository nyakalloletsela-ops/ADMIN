#!/usr/bin/env python3
"""ADMIN server entrypoint.

The production implementation lives in production.py so the executable entry
point stays stable for local and deployment commands.
"""
import os
from datetime import date
import production as app

# A newly installed ADMIN instance must not report scheduler backfill as if it
# were historical business activity.  We persist the operational start date so
# overdue metrics become meaningful from the first real operating day onward.
def establish_operational_start():
    c = app.db()
    c.execute("CREATE TABLE IF NOT EXISTS admin_runtime_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    configured = os.getenv("ADMIN_OPERATION_START_DATE", "").strip()
    if configured:
        try:
            date.fromisoformat(configured)
        except ValueError as exc:
            c.close()
            raise SystemExit("ADMIN_OPERATION_START_DATE must be YYYY-MM-DD") from exc
    existing = c.execute(
        "SELECT value FROM admin_runtime_meta WHERE key='operational_start_date'"
    ).fetchone()
    if not existing:
        start = configured or date.today().isoformat()
        c.execute(
            "INSERT INTO admin_runtime_meta(key,value) VALUES('operational_start_date',?)",
            (start,),
        )
    c.commit()
    row = c.execute(
        "SELECT value FROM admin_runtime_meta WHERE key='operational_start_date'"
    ).fetchone()
    c.close()
    return row[0]


def production_summary():
    """Return dashboard metrics without counting pre-operational backfill."""
    result = app._ORIGINAL_SUMMARY()
    c = app.db()
    start_row = c.execute(
        "SELECT value FROM admin_runtime_meta WHERE key='operational_start_date'"
    ).fetchone()
    start = start_row[0] if start_row else date.today().isoformat()
    today = date.today().isoformat()

    due_today = c.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE due_date=? AND status NOT IN ('COMPLETED','CANCELLED')
             AND due_date>=?""",
        (today, start),
    ).fetchone()[0]
    overdue = c.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE due_date<? AND due_date>=?
             AND status NOT IN ('COMPLETED','CANCELLED')""",
        (today, start),
    ).fetchone()[0]
    open_tasks = c.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE due_date<=? AND due_date>=?
             AND status NOT IN ('COMPLETED','CANCELLED')""",
        (today, start),
    ).fetchone()[0]
    completed_7d = c.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE status='COMPLETED' AND completed_at>=?""",
        (start,),
    ).fetchone()[0]
    upcoming = c.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE due_date>? AND status NOT IN ('COMPLETED','CANCELLED')""",
        (today,),
    ).fetchone()[0]
    c.close()

    result['tasks'].update({
        'due_today': due_today,
        'overdue': overdue,
        'open': open_tasks,
        'completed_7d': completed_7d,
        'scheduled_upcoming': upcoming,
    })
    return result


# Preserve the domain implementation and replace only the dashboard aggregation.
app._ORIGINAL_SUMMARY = app.summary
app.summary = production_summary


if __name__ == '__main__':
    app.init()
    establish_operational_start()
    app.materialize()
    import threading
    threading.Thread(target=app.worker, daemon=True).start()
    print(f'ADMIN production server on http://127.0.0.1:{app.PORT}')
    app.ThreadingHTTPServer((app.HOST, app.PORT), app.H).serve_forever()
