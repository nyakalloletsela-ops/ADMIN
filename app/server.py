#!/usr/bin/env python3
"""ADMIN production server entrypoint.

The domain/API implementation remains in production.py. This entrypoint owns
startup lifecycle concerns so a fresh installation starts its operational task
schedule on the current day instead of manufacturing historical work.
"""
import os
import threading
import time
from datetime import date, timedelta
import production as app


def establish_operational_start():
    """Persist the first real operating day for this ADMIN database."""
    c = app.db()
    c.execute(
        "CREATE TABLE IF NOT EXISTS admin_runtime_meta "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
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


def materialize_current_schedule():
    """Materialize only today and future scheduled occurrences."""
    c = app.db()
    today = date.today()
    templates = list(c.execute("SELECT * FROM task_templates WHERE active=1"))

    for template in templates:
        d = today
        while d <= today + timedelta(days=14):
            due = (
                template["cadence"] == "daily"
                or (template["cadence"] == "weekly" and d.weekday() == 0)
                or (template["cadence"] == "monthly" and d.day == 1)
                or (
                    template["cadence"] == "quarterly"
                    and d.day == 1
                    and d.month in (1, 4, 7, 10)
                )
            )
            if due:
                c.execute(
                    """INSERT OR IGNORE INTO tasks(
                        template_id,title,area,responsible,priority,due_date,
                        status,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        template["id"],
                        template["title"],
                        template["area"],
                        template["responsible"],
                        template["priority"],
                        d.isoformat(),
                        "PENDING",
                        app.now(),
                        app.now(),
                    ),
                )
            d += timedelta(days=1)

    today_s = today.isoformat()
    for task in c.execute(
        "SELECT id,title,due_date FROM tasks "
        "WHERE status NOT IN ('COMPLETED','CANCELLED') AND due_date=?",
        (today_s,),
    ):
        c.execute(
            "INSERT OR IGNORE INTO reminders(task_id,kind,message,due_at) "
            "VALUES(?,?,?,?)",
            (task["id"], "due", "Due today: " + task["title"], app.now()),
        )

    c.commit()
    c.close()


def remove_legacy_backfill(start):
    """Remove only uncompleted task occurrences predating the start date."""
    c = app.db()
    old_ids = [
        row[0]
        for row in c.execute(
            "SELECT id FROM tasks WHERE due_date<? "
            "AND status NOT IN ('COMPLETED','CANCELLED')",
            (start,),
        ).fetchall()
    ]
    if old_ids:
        placeholders = ",".join("?" for _ in old_ids)
        c.execute(
            f"DELETE FROM reminders WHERE task_id IN ({placeholders})", old_ids
        )
        c.execute(
            f"DELETE FROM tasks WHERE id IN ({placeholders})", old_ids
        )
    c.commit()
    c.close()


def production_summary():
    """Return dashboard metrics for the actual operating window."""
    result = app._ORIGINAL_SUMMARY()
    c = app.db()
    start_row = c.execute(
        "SELECT value FROM admin_runtime_meta WHERE key='operational_start_date'"
    ).fetchone()
    start = start_row[0] if start_row else date.today().isoformat()
    today = date.today().isoformat()
    seven_days_ago = max(start, (date.today() - timedelta(days=7)).isoformat())

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
        (seven_days_ago,),
    ).fetchone()[0]
    upcoming = c.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE due_date>? AND status NOT IN ('COMPLETED','CANCELLED')""",
        (today,),
    ).fetchone()[0]
    c.close()

    result["tasks"].update({
        "due_today": due_today,
        "overdue": overdue,
        "open": open_tasks,
        "completed_7d": completed_7d,
        "scheduled_upcoming": upcoming,
    })
    return result


def scheduler_loop():
    """Run ADMIN's safe scheduler and continuously repair legacy backfill."""
    while True:
        try:
            # Keep the database clean even if an older ADMIN process or legacy
            # scheduler has previously inserted historical open occurrences.
            start = establish_operational_start()
            remove_legacy_backfill(start)
            materialize_current_schedule()
        except Exception as exc:
            print("scheduler:", exc)
        time.sleep(60)


app._ORIGINAL_SUMMARY = app.summary
app.summary = production_summary


if __name__ == "__main__":
    app.init()
    start = establish_operational_start()
    remove_legacy_backfill(start)
    materialize_current_schedule()

    threading.Thread(target=scheduler_loop, daemon=True).start()
    print(f"ADMIN production server on http://127.0.0.1:{app.PORT}")
    app.ThreadingHTTPServer((app.HOST, app.PORT), app.H).serve_forever()
