#!/usr/bin/env python3
"""
ADMIN — Reference prototype for the Administrative Officer (Farm & Property Management)
automation architecture.

Zero external dependencies (Python 3 stdlib only).

What it demonstrates (the workplan's control cycle):
  PLAN      -> recurring tasks are auto-generated from templates on their due date
  ASSIGN    -> each task carries a responsible role, priority and deadline
  EXECUTE   -> tasks move Pending -> In Progress -> Completed
  MONITOR   -> overdue detection + reminders
  VERIFY    -> completion recorded with timestamp
  RECORD    -> every event persists in a single system of record (SQLite)
  REPORT    -> auto-compiled weekly summary + JSON API
  FOLLOW UP -> overdue items auto-generate reminders for escalation

Run:
    python3 server.py            # serves http://0.0.0.0:8000
"""

import json
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DB_PATH = "admin.db"
HOST, PORT = "0.0.0.0", 8000

# --------------------------------------------------------------------------- #
# 1. Task templates — the automation keystone (one row per recurring activity)
#    Derived from the "Coordination of Key Tasks Workplan".
# --------------------------------------------------------------------------- #
TEMPLATES = [
    # (area, task, cadence, weekday(Mon=0)/None, day-of-month/None, responsible, admin_role, indicator, level, priority)
    ("Farm Operations", "Coordinate crop & livestock activities", "daily", None, None,
     "Farm Supervisor / Caretakers", "Plan, coordinate and monitor",
     "Activities completed as scheduled", "PARTIAL", "High"),
    ("Livestock", "Livestock feeding, watering & health checks", "daily", None, None,
     "Caretakers / Workers", "Monitor and verify",
     "Animals properly cared for; records updated", "PARTIAL", "High"),
    ("Farm Workers", "Attendance, duty allocation & supervision", "daily", None, None,
     "Supervisor", "Monitor attendance and performance",
     "High task-completion rate", "PARTIAL", "High"),
    ("Daily Coordination", "Daily coordination routine (morning / midday / end-of-day)", "daily", None, None,
     "Administrative Officer", "Run daily routine",
     "Routine completed and logged", "PARTIAL", "High"),
    ("Maintenance", "Log & coordinate repairs, defects & preventative maintenance", "daily", None, None,
     "Caretakers / Contractors", "Log and coordinate work",
     "Jobs tracked to completion", "PARTIAL", "Medium"),
    ("Records", "Maintain registers, logs, invoices & supporting documents", "daily", None, None,
     "Administrative Officer", "Maintain and file records",
     "Records complete and current", "FULL", "Medium"),
    ("Weekly Planning", "Weekly planning: review outstanding work & allocate priorities", "weekly", 0, None,
     "Administrative Officer", "Establish weekly priorities",
     "Priorities set for the week", "PARTIAL", "High"),
    ("Property Management", "Property inspections & condition monitoring", "weekly", 2, None,
     "Caretakers", "Coordinate inspections and reports",
     "Inspection reports completed", "PARTIAL", "Medium"),
    ("Reporting", "Weekly performance review & management report", "weekly", 4, None,
     "Administrative Officer", "Compile and submit report",
     "Report submitted on time", "FULL", "High"),
    ("Accommodation", "Occupancy, vacancies, leases & occupant records review", "monthly", None, 1,
     "Administrative Officer", "Maintain portfolio records",
     "Accurate occupancy records", "FULL", "Medium"),
    ("Stock Control", "Stock count: feed, seed, fertiliser, cleaning materials, supplies", "monthly", None, 1,
     "Responsible Staff", "Verify records and stock levels",
     "Minimal unexplained variances", "PARTIAL", "Medium"),
    ("Reporting", "Monthly management report", "monthly", None, 1,
     "Administrative Officer", "Compile and submit report",
     "Report submitted on time", "FULL", "High"),
    ("Assets", "Asset register audit (equipment & property)", "quarterly", None, 1,
     "Administrative Officer", "Maintain asset register",
     "Assets accounted for", "PARTIAL", "Low"),
    ("Crop Production", "Planting, weeding, fertilising, irrigation & harvesting", "seasonal", None, None,
     "Farm Workers", "Maintain schedule and records",
     "Crop activities completed on time", "PARTIAL", "Medium"),
    # Event-driven (not auto-scheduled; created on occurrence):
    ("Tenant Matters", "Tenant complaints, requests & follow-up", "event", None, None,
     "Admin Officer / Caretaker", "Log, coordinate and escalate",
     "Issues resolved within agreed time", "PARTIAL", "Medium"),
    ("Procurement", "Farm/property supplies & services", "event", None, None,
     "Administrative Officer", "Coordinate requests and approvals",
     "Approved purchases documented", "PARTIAL", "Medium"),
    ("Incidents", "Loss, damage, illness, theft, accidents, disputes", "event", None, None,
     "All Staff", "Record, escalate and follow up",
     "Incidents reported promptly", "PARTIAL", "High"),
]


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = connect()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS templates(
            id INTEGER PRIMARY KEY,
            area TEXT, task TEXT, cadence TEXT,
            weekday INTEGER, dom INTEGER,
            responsible TEXT, admin_role TEXT, indicator TEXT,
            level TEXT, priority TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER,
            title TEXT NOT NULL,
            area TEXT,
            responsible TEXT,
            priority TEXT DEFAULT 'Medium',
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            follow_up_of INTEGER,
            note TEXT,
            created_at TEXT,
            completed_at TEXT,
            UNIQUE(template_id, due_date)
        );
        CREATE TABLE IF NOT EXISTS reminders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            kind TEXT,              -- 'due' | 'overdue' | 'follow_up'
            message TEXT,
            due_at TEXT,
            delivered INTEGER DEFAULT 0,
            UNIQUE(task_id, kind)
        );
        CREATE TABLE IF NOT EXISTS tenants(
            id INTEGER PRIMARY KEY, name TEXT, phone TEXT, unit TEXT,
            lease_end TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY, tenant_id INTEGER, amount REAL,
            due_date TEXT, paid INTEGER DEFAULT 0, paid_at TEXT
        );
        CREATE TABLE IF NOT EXISTS maintenance_requests(
            id INTEGER PRIMARY KEY, tenant_id INTEGER, description TEXT,
            priority TEXT, status TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS stock_items(
            id INTEGER PRIMARY KEY, name TEXT, category TEXT,
            qty REAL, reorder_level REAL
        );
        CREATE TABLE IF NOT EXISTS assets(
            id INTEGER PRIMARY KEY, name TEXT, category TEXT,
            location TEXT, status TEXT, last_audit TEXT
        );
        CREATE TABLE IF NOT EXISTS incidents(
            id INTEGER PRIMARY KEY, type TEXT, description TEXT,
            severity TEXT, status TEXT, reported_at TEXT
        );
        """
    )

    # Seed templates
    cur = con.execute("SELECT COUNT(*) AS c FROM templates")
    if cur.fetchone()["c"] == 0:
        con.executemany(
            "INSERT INTO templates(area,task,cadence,weekday,dom,responsible,admin_role,indicator,level,priority)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            TEMPLATES,
        )

    # Seed sample system-of-record entities (demo data)
    cur = con.execute("SELECT COUNT(*) AS c FROM tenants")
    if cur.fetchone()["c"] == 0:
        today = date.today()
        con.executemany(
            "INSERT INTO tenants(name,phone,unit,lease_end,status) VALUES(?,?,?,?,?)",
            [
                ("M. Tau", "+266 5xxx 0101", "House 1", (today + timedelta(days=160)).isoformat(), "Active"),
                ("L. Mofokeng", "+266 5xxx 0102", "House 3", (today + timedelta(days=45)).isoformat(), "Active"),
                ("P. Nkosi", "+266 5xxx 0103", "Flat 2A", (today - timedelta(days=12)).isoformat(), "Expiring"),
                ("S. Dlamini", "+266 5xxx 0104", "House 7", (today + timedelta(days=300)).isoformat(), "Active"),
            ],
        )
        con.executemany(
            "INSERT INTO invoices(tenant_id,amount,due_date,paid) VALUES(?,?,?,?)",
            [
                (1, 2500.0, today.isoformat(), 0),
                (2, 2500.0, today.isoformat(), 0),
                (3, 1800.0, (today - timedelta(days=28)).isoformat(), 0),  # arrears
                (4, 2500.0, today.isoformat(), 1),
            ],
        )
        con.executemany(
            "INSERT INTO maintenance_requests(tenant_id,description,priority,status,created_at) VALUES(?,?,?,?,?)",
            [
                (1, "Leaking roof in kitchen", "High", "Open", today.isoformat()),
                (3, "Broken gate lock", "Medium", "Open", (today - timedelta(days=3)).isoformat()),
            ],
        )
        con.executemany(
            "INSERT INTO stock_items(name,category,qty,reorder_level) VALUES(?,?,?,?)",
            [
                ("Cattle feed (bags)", "Feed", 12, 20),
                ("Maize seed (kg)", "Seed", 40, 10),
                ("Fertiliser (bags)", "Fertiliser", 8, 15),
                ("Cleaning materials", "Supplies", 25, 10),
                ("Diesel (litres)", "Fuel", 90, 50),
            ],
        )
        con.executemany(
            "INSERT INTO assets(name,category,location,status,last_audit) VALUES(?,?,?,?,?)",
            [
                ("Tractor — Massey 135", "Machinery", "Farm yard", "In use", None),
                ("Water pump — borehole 2", "Equipment", "Borehole", "In use", None),
                ("House 1 — fridge", "Furnishing", "House 1", "In use", None),
                ("Generator — 5kVA", "Equipment", "Store", "Spare", None),
            ],
        )
        con.executemany(
            "INSERT INTO incidents(type,description,severity,status,reported_at) VALUES(?,?,?,?,?)",
            [
                ("Damage", "Fence cut near paddock B", "Medium", "Open", today.isoformat()),
            ],
        )
    con.commit()
    con.close()


# --------------------------------------------------------------------------- #
# 2. Scheduler — PLAN/ASSIGN: materialise recurring tasks from templates
# --------------------------------------------------------------------------- #
def due_for(template, d):
    cadence = template["cadence"]
    if cadence == "daily":
        return True
    if cadence == "weekly":
        return d.weekday() == template["weekday"]
    if cadence == "monthly":
        return d.day == template["dom"]
    if cadence == "quarterly":
        return d.day == template["dom"] and d.month in (1, 4, 7, 10)
    # 'seasonal' and 'event' are not auto-scheduled
    return False


def ensure_tasks():
    """Generate every due task for the window [today-30 .. today+21]."""
    con = connect()
    templates = [dict(r) for r in con.execute("SELECT * FROM templates")]
    today = date.today()
    # Backfill a short history so escalation is visible, and schedule 2 weeks ahead.
    start, end = today - timedelta(days=4), today + timedelta(days=14)
    d = start
    while d <= end:
        for t in templates:
            if due_for(t, d):
                con.execute(
                    "INSERT OR IGNORE INTO tasks(template_id,title,area,responsible,priority,due_date,status,created_at)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (t["id"], t["task"], t["area"], t["responsible"], t["priority"],
                     d.isoformat(), "Pending", datetime.now().isoformat(timespec="seconds")),
                )
        d += timedelta(days=1)
    con.commit()
    con.close()


def ensure_reminders():
    """MONITOR/FOLLOW UP: create reminders for tasks due today and overdue."""
    con = connect()
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")

    # Due today, not completed
    due_today = con.execute(
        "SELECT id,title FROM tasks WHERE due_date=? AND status!='Completed'", (today,)
    ).fetchall()
    # Overdue, not completed
    overdue = con.execute(
        "SELECT id,title FROM tasks WHERE due_date<? AND status!='Completed'", (today,)
    ).fetchall()

    for t in due_today:
        con.execute(
            "INSERT OR IGNORE INTO reminders(task_id,kind,message,due_at) VALUES(?,?,?,?)",
            (t["id"], "due", f"Due today: {t['title']}", today),
        )
    for t in overdue:
        con.execute(
            "INSERT OR IGNORE INTO reminders(task_id,kind,message,due_at) VALUES(?,?,?,?)",
            (t["id"], "overdue", f"OVERDUE — escalate: {t['title']}", today),
        )
    con.commit()
    con.close()


def scheduler_loop():
    while True:
        try:
            ensure_tasks()
            ensure_reminders()
        except Exception as exc:  # keep the loop alive on any error
            print("scheduler error:", exc)
        time.sleep(60)


# --------------------------------------------------------------------------- #
# 3. Queries
# --------------------------------------------------------------------------- #
def fetch_summary():
    con = connect()
    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    one = "SELECT COUNT(*) AS c FROM "

    due_today = con.execute(one + "tasks WHERE due_date=? AND status!='Completed'", (today,)).fetchone()["c"]
    overdue = con.execute(one + "tasks WHERE due_date<? AND status!='Completed'", (today,)).fetchone()["c"]
    pending = con.execute(one + "tasks WHERE status IN ('Pending','In Progress')").fetchone()["c"]
    completed_7d = con.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status='Completed' AND completed_at>=?",
        ((date.today() - timedelta(days=7)).isoformat(),),
    ).fetchone()["c"]
    open_maintenance = con.execute(one + "maintenance_requests WHERE status='Open'").fetchone()["c"]
    arrears = con.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(amount),0) AS t FROM invoices WHERE paid=0 AND due_date<?",
        (today,),
    ).fetchone()
    low_stock = con.execute(one + "stock_items WHERE qty <= reorder_level").fetchone()["c"]
    open_incidents = con.execute(one + "incidents WHERE status='Open'").fetchone()["c"]
    reminders = con.execute(one + "reminders WHERE delivered=0").fetchone()["c"]

    # Weekly review (matches the workplan's "Weekly Performance Review")
    planned_week = con.execute(
        one + "tasks WHERE due_date>=? AND due_date<=? AND status!='Completed'",
        (week_start, (date.today() + timedelta(days=6)).isoformat()),
    ).fetchone()["c"]
    completed_week = con.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE status='Completed' AND completed_at>=?", (week_start,)
    ).fetchone()["c"]
    outstanding = due_today
    delayed = overdue
    con.close()

    return {
        "date": today,
        "tasks": {"due_today": due_today, "overdue": overdue, "pending": pending,
                   "completed_7d": completed_7d},
        "operations": {"open_maintenance": open_maintenance, "open_incidents": open_incidents},
        "finance": {"arrears_count": arrears["c"], "arrears_total": arrears["t"]},
        "stock": {"low_stock": low_stock},
        "reminders_pending": reminders,
        "weekly_review": {
            "week_start": week_start,
            "planned": planned_week, "completed": completed_week,
            "outstanding": outstanding, "delayed": delayed,
        },
    }


def fetch_tasks(status=None, area=None, q=None, limit=200):
    con = connect()
    sql = "SELECT * FROM tasks"
    where, params = [], []
    if status:
        where.append("status=?"); params.append(status)
    if area:
        where.append("area=?"); params.append(area)
    if q:
        where.append("(title LIKE ? OR responsible LIKE ? OR area LIKE ?)")
        params += [f"%{q}%"] * 3
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY CASE status WHEN 'Overdue' THEN 0 WHEN 'Pending' THEN 1 "
    sql += "WHEN 'In Progress' THEN 2 ELSE 3 END, due_date ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in con.execute(sql, params)]
    con.close()

    # annotate overdue
    today = date.today().isoformat()
    for r in rows:
        r["is_overdue"] = r["status"] != "Completed" and r["due_date"] < today
    return rows


# --------------------------------------------------------------------------- #
# 4. HTTP server
# --------------------------------------------------------------------------- #
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADMIN — Farm &amp; Property Automation</title>
<style>
  :root{--ink:#1a2b22;--paper:#f7f5f0;--card:#ffffff;--brand:#2f6b4f;--amber:#c77d1f;--red:#b3442c;--line:#e3dfd4}
  *{box-sizing:border-box}
  body{margin:0;font:15px/1.45 system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:var(--paper);color:var(--ink)}
  header{background:var(--brand);color:#fff;padding:18px 26px}
  header h1{margin:0;font-size:20px}
  header p{margin:4px 0 0;opacity:.85;font-size:13px}
  main{padding:22px 26px 60px;max-width:1180px;margin:0 auto}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:22px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
  .card .n{font-size:26px;font-weight:700}
  .card .l{font-size:12px;color:#6b6b6b;text-transform:uppercase;letter-spacing:.03em}
  .card.warn .n{color:var(--red)} .card.ok .n{color:var(--brand)} .card.amber .n{color:var(--amber)}
  .panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:18px}
  .panel h2{margin:0 0 10px;font-size:16px}
  table{width:100%;border-collapse:collapse;font-size:13.5px}
  th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
  th{font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#6b6b6b}
  .pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600}
  .P{background:#eef3f0;color:#2f6b4f}.I{background:#eaf2fb;color:#2b5c9e}.C{background:#e6f4ea;color:#1f7a3d}
  .E{background:#fdeeee;color:#b3442c}.OV{background:#fdeeee;color:#b3442c}
  .filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
  .filters select,.filters input,.addrow input,.addrow select{border:1px solid var(--line);border-radius:8px;padding:7px 10px;font:inherit}
  .filters button,.addrow button,.act{background:var(--brand);color:#fff;border:0;border-radius:8px;padding:7px 12px;cursor:pointer;font:inherit}
  .addrow{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
  .muted{color:#6b6b6b;font-size:12.5px}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
  @media(max-width:820px){.two{grid-template-columns:1fr}}
  .review td:first-child{font-weight:600;width:180px}
  code{background:#eee9dc;padding:1px 6px;border-radius:6px;font-size:12.5px}
</style>
</head>
<body>
<header>
  <h1>ADMIN — Farm &amp; Property Automation</h1>
  <p>Reference prototype · PLAN → ASSIGN → EXECUTE → MONITOR → VERIFY → RECORD → REPORT → FOLLOW UP</p>
</header>
<main>
  <div class="cards" id="cards"></div>
  <div class="two">
    <div class="panel">
      <h2>Task Tracking Register</h2>
      <div class="filters">
        <select id="fStatus"><option value="">All statuses</option>
          <option>Pending</option><option>In Progress</option><option>Completed</option></select>
        <input id="fQ" placeholder="Search task / person / area…">
        <button onclick="loadTasks()">Filter</button>
      </div>
      <div class="addrow">
        <input id="nTitle" placeholder="New task…">
        <input id="nResp" placeholder="Responsible">
        <select id="nPrio"><option>Medium</option><option>High</option><option>Low</option></select>
        <input id="nDue" type="date">
        <button onclick="addTask()">+ Add</button>
      </div>
      <div style="overflow-x:auto"><table>
        <thead><tr><th>Task</th><th>Area</th><th>Responsible</th><th>Priority</th><th>Due</th><th>Status</th><th></th></tr></thead>
        <tbody id="tasks"></tbody>
      </table></div>
      <p class="muted">Click a status button to advance: Pending → In Progress → Completed. Overdue items are flagged and auto-reminded.</p>
    </div>
    <div>
      <div class="panel">
        <h2>Weekly Performance Review <span class="muted" id="weekSpan"></span></h2>
        <table class="review"><tbody id="review"></tbody></table>
      </div>
      <div class="panel">
        <h2>Upcoming reminders</h2>
        <ul id="reminders" style="margin:0;padding-left:18px"></ul>
      </div>
    </div>
  </div>
</main>
<script>
const $=id=>document.getElementById(id);
async function j(url,opts){const r=await fetch(url,opts);return r.json();}
function pill(s){const m={'Pending':'P','In Progress':'I','Completed':'C','Escalated':'E'};return `<span class="pill ${m[s]||''}">${s}</span>`;}
async function loadSummary(){
  const s=await j('/api/summary');
  const c=(n,l,cls)=>`<div class="card ${cls}"><div class="n">${n}</div><div class="l">${l}</div></div>`;
  $('cards').innerHTML=
    c(s.tasks.due_today,'Due today','ok')+
    c(s.tasks.overdue,'Overdue','warn')+
    c(s.tasks.pending,'Open tasks','ok')+
    c(s.operations.open_maintenance,'Open maintenance','amber')+
    c(s.finance.arrears_count,`Tenants in arrears (R${s.finance.arrears_total.toLocaleString()})`,'warn')+
    c(s.stock.low_stock,'Items low stock','amber')+
    c(s.operations.open_incidents,'Open incidents','warn')+
    c(s.tasks.completed_7d,'Completed (7d)','ok');
  const w=s.weekly_review;
  $('weekSpan').textContent=`(week of ${w.week_start})`;
  $('review').innerHTML=
    `<tr><td>Tasks planned</td><td>${w.planned}</td></tr>`+
    `<tr><td>Tasks completed</td><td>${w.completed}</td></tr>`+
    `<tr><td>Outstanding (due today)</td><td>${w.outstanding}</td></tr>`+
    `<tr><td>Delayed (overdue)</td><td>${w.delayed}</td></tr>`+
    `<tr><td>Reminders pending</td><td>${s.reminders_pending}</td></tr>`;
  const rem=await j('/api/reminders');
  $('reminders').innerHTML=rem.map(r=>`<li>${r.message} <span class="muted">[${r.kind}]</span></li>`).join('')||'<li class="muted">No pending reminders.</li>';
}
async function loadTasks(){
  const st=$('fStatus').value, q=encodeURIComponent($('fQ').value.trim());
  const rows=await j(`/api/tasks?status=${st}&q=${q}`);
  $('tasks').innerHTML=rows.map(r=>`
    <tr>
      <td>${r.title}${r.is_overdue?' <span class="pill OV">Overdue</span>':''}</td>
      <td>${r.area||''}</td><td>${r.responsible||''}</td><td>${r.priority||''}</td>
      <td>${r.due_date}</td><td>${pill(r.status)}</td>
      <td><button class="act" onclick="advance(${r.id},'${r.status}')">▸</button></td>
    </tr>`).join('')||'<tr><td colspan="7" class="muted">No tasks match.</td></tr>';
}
async function advance(id,status){
  const next=status==='Pending'?'In Progress':status==='In Progress'?'Completed':'Completed';
  await j(`/api/tasks/${id}/status`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:next})});
  loadTasks();loadSummary();
}
async function addTask(){
  const due=$('nDue').value||new Date().toISOString().slice(0,10);
  await j('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({title:$('nTitle').value,responsible:$('nResp').value,priority:$('nPrio').value,due_date:due})});
  $('nTitle').value='';$('nResp').value='';loadTasks();loadSummary();
}
loadSummary();loadTasks();
</script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)
        if path == "/":
            return self._send(200, PAGE, "text/html")
        if path == "/api/health":
            return self._send(200, {"ok": True, "now": datetime.now().isoformat()})
        if path == "/api/summary":
            return self._send(200, fetch_summary())
        if path == "/api/tasks":
            return self._send(200, fetch_tasks(
                status=qs.get("status", [""])[0] or None,
                area=qs.get("area", [""])[0] or None,
                q=qs.get("q", [""])[0] or None,
            ))
        if path == "/api/templates":
            con = connect()
            rows = [dict(r) for r in con.execute("SELECT * FROM templates")]
            con.close()
            return self._send(200, rows)
        if path == "/api/reminders":
            con = connect()
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM reminders WHERE delivered=0 ORDER BY due_at")][:20]
            con.close()
            return self._send(200, rows)
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        try:
            if path == "/api/tasks":
                b = self._read_json()
                con = connect()
                cur = con.execute(
                    "INSERT INTO tasks(title,responsible,priority,due_date,status,created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (b.get("title", "Untitled"), b.get("responsible", "Administrative Officer"),
                     b.get("priority", "Medium"), b.get("due_date", date.today().isoformat()),
                     "Pending", datetime.now().isoformat(timespec="seconds")),
                )
                con.commit()
                con.close()
                return self._send(201, {"id": cur.lastrowid})
            if len(parts) == 4 and parts[1] == "tasks" and parts[3] == "status":
                tid = int(parts[2])
                b = self._read_json()
                con = connect()
                status = b.get("status", "Pending")
                completed_at = datetime.now().isoformat(timespec="seconds") if status == "Completed" else None
                con.execute("UPDATE tasks SET status=?, completed_at=? WHERE id=?", (status, completed_at, tid))
                if status == "Completed":
                    con.execute("UPDATE reminders SET delivered=1 WHERE task_id=?", (tid,))
                con.commit()
                con.close()
                return self._send(200, {"ok": True})
        except Exception as exc:
            return self._send(400, {"error": str(exc)})
        return self._send(404, {"error": "not found"})

    def log_message(self, *a):
        pass  # quiet


def main():
    init_db()
    ensure_tasks()
    ensure_reminders()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ADMIN prototype running on http://{HOST}:{PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
