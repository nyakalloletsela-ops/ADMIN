#!/usr/bin/env python3
"""ADMIN: runnable farm/property operations application.

Zero third-party dependencies. SQLite is the local persistence adapter; the
business-facing API is isolated under /api/v1 so PostgreSQL can replace it.
No external provider or credential is hard-coded.
"""
import base64, hashlib, hmac, json, os, secrets, sqlite3, threading, time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST=os.getenv("ADMIN_HOST","0.0.0.0"); PORT=int(os.getenv("ADMIN_PORT","8000"))
DB_PATH=os.getenv("ADMIN_DB","admin.db"); COOKIE="admin_session"
SESSION_TTL=8*60*60
STATUSES=("PENDING","ASSIGNED","IN_PROGRESS","BLOCKED","SUBMITTED","VERIFICATION_REQUIRED","COMPLETED","CANCELLED")
PRIORITIES=("LOW","MEDIUM","HIGH","URGENT")
TEMPLATES=[
("Farm Operations","Coordinate crop & livestock activities","daily","Farm Supervisor / Caretakers","HIGH"),
("Livestock","Livestock feeding, watering & health checks","daily","Caretakers / Workers","HIGH"),
("Farm Workers","Attendance, duty allocation & supervision","daily","Supervisor","HIGH"),
("Daily Coordination","Morning / midday / end-of-day coordination","daily","Administrative Officer","HIGH"),
("Maintenance","Log and coordinate repairs and preventative maintenance","daily","Caretakers / Contractors","MEDIUM"),
("Records","Maintain registers, logs, invoices and supporting documents","daily","Administrative Officer","MEDIUM"),
("Weekly Planning","Review outstanding work and allocate priorities","weekly","Administrative Officer","HIGH"),
("Property Management","Property inspections and condition monitoring","weekly","Caretakers","MEDIUM"),
("Reporting","Weekly performance review and management report","weekly","Administrative Officer","HIGH"),
("Accommodation","Occupancy, vacancies, leases and occupant records review","monthly","Administrative Officer","MEDIUM"),
("Stock Control","Stock count and variance review","monthly","Responsible Staff","MEDIUM"),
("Reporting","Monthly management report","monthly","Administrative Officer","HIGH"),
("Assets","Asset register audit","quarterly","Administrative Officer","LOW"),
]
SESSIONS={}; SESSIONS_LOCK=threading.Lock()

def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def connect():
    c=sqlite3.connect(DB_PATH,timeout=15); c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); c.execute("PRAGMA journal_mode=WAL"); return c

def password_hash(p,salt=None):
    salt=salt or secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256",p.encode(),salt,210000)
    return base64.urlsafe_b64encode(salt).decode()+"$"+base64.urlsafe_b64encode(digest).decode()
def password_ok(p,stored):
    try:
        a,b=stored.split("$",1); salt=base64.urlsafe_b64decode(a); expected=base64.urlsafe_b64decode(b)
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",p.encode(),salt,210000),expected)
    except Exception: return False

def audit(c,actor,action,entity,entity_id,before=None,after=None):
    c.execute("INSERT INTO audit_log(actor,action,entity,entity_id,before_json,after_json,created_at) VALUES(?,?,?,?,?,?,?)",
              (actor,action,entity,str(entity_id),json.dumps(before,sort_keys=True) if before else None,json.dumps(after,sort_keys=True) if after else None,now()))

def init_db():
    c=connect(); c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS task_templates(id INTEGER PRIMARY KEY AUTOINCREMENT,area TEXT NOT NULL,title TEXT NOT NULL,cadence TEXT NOT NULL,responsible TEXT NOT NULL,priority TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,UNIQUE(area,title));
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,template_id INTEGER,title TEXT NOT NULL,area TEXT,responsible TEXT,priority TEXT NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',note TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,completed_at TEXT,FOREIGN KEY(template_id) REFERENCES task_templates(id),UNIQUE(template_id,due_date));
    CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id INTEGER NOT NULL,kind TEXT NOT NULL,message TEXT NOT NULL,due_at TEXT NOT NULL,delivered INTEGER NOT NULL DEFAULT 0,UNIQUE(task_id,kind),FOREIGN KEY(task_id) REFERENCES tasks(id));
    CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,address TEXT,status TEXT NOT NULL DEFAULT 'ACTIVE');
    CREATE TABLE IF NOT EXISTS units(id INTEGER PRIMARY KEY AUTOINCREMENT,property_id INTEGER NOT NULL,name TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'VACANT',rent_amount REAL NOT NULL DEFAULT 0,FOREIGN KEY(property_id) REFERENCES properties(id));
    CREATE TABLE IF NOT EXISTS tenants(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT,email TEXT,unit_id INTEGER,status TEXT NOT NULL DEFAULT 'ACTIVE',lease_end TEXT,created_at TEXT NOT NULL,FOREIGN KEY(unit_id) REFERENCES units(id));
    CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY AUTOINCREMENT,tenant_id INTEGER NOT NULL,amount REAL NOT NULL,due_date TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(tenant_id) REFERENCES tenants(id));
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_id INTEGER NOT NULL,amount REAL NOT NULL,reference TEXT NOT NULL,received_at TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(invoice_id) REFERENCES invoices(id));
    CREATE TABLE IF NOT EXISTS maintenance(id INTEGER PRIMARY KEY AUTOINCREMENT,tenant_id INTEGER,description TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'REPORTED',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(tenant_id) REFERENCES tenants(id));
    CREATE TABLE IF NOT EXISTS stock_items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT,reorder_level REAL NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER NOT NULL,quantity REAL NOT NULL,kind TEXT NOT NULL,reference TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(item_id) REFERENCES stock_items(id));
    CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT,location TEXT,status TEXT NOT NULL DEFAULT 'IN_USE',last_audit TEXT);
    CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT NOT NULL,description TEXT NOT NULL,severity TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'REPORTED',reported_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS integration_settings(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT UNIQUE NOT NULL,provider TEXT,status TEXT NOT NULL DEFAULT 'NOT_CONFIGURED',config_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,entity TEXT NOT NULL,entity_id TEXT,before_json TEXT,after_json TEXT,created_at TEXT NOT NULL);
    """)
    if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        pw=os.getenv("ADMIN_PASSWORD")
        if not pw: pw=secrets.token_urlsafe(24)
        c.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES('admin',?,'SYSTEM_ADMIN',?)",(password_hash(pw),now()))
        print("ADMIN bootstrap password:",pw if not os.getenv("ADMIN_PASSWORD") else "configured by ADMIN_PASSWORD")
    for row in TEMPLATES:
        c.execute("INSERT OR IGNORE INTO task_templates(area,title,cadence,responsible,priority) VALUES(?,?,?,?,?)",row)
    c.commit(); c.close()

def materialize():
    c=connect(); today=date.today(); start=today-timedelta(days=4); end=today+timedelta(days=14)
    for t in c.execute("SELECT * FROM task_templates WHERE active=1"):
        d=start
        while d<=end:
            due=(t["cadence"]=="daily" or (t["cadence"]=="weekly" and d.weekday()==0) or (t["cadence"]=="monthly" and d.day==1) or (t["cadence"]=="quarterly" and d.day==1 and d.month in (1,4,7,10)))
            if due: c.execute("INSERT OR IGNORE INTO tasks(template_id,title,area,responsible,priority,due_date,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?, ?,?)",(t["id"],t["title"],t["area"],t["responsible"],t["priority"],d.isoformat(),"PENDING",now(),now()))
            d+=timedelta(days=1)
    today_s=today.isoformat()
    for r in c.execute("SELECT id,title FROM tasks WHERE status!='COMPLETED' AND due_date<=?",(today_s,)):
        kind="due" if r["id"] and True else "due"
        if c.execute("SELECT 1 FROM tasks WHERE id=? AND due_date=?",(r["id"],today_s)).fetchone(): msg="Due today: "+r["title"]
        else: kind="overdue"; msg="OVERDUE: "+r["title"]
        c.execute("INSERT OR IGNORE INTO reminders(task_id,kind,message,due_at) VALUES(?,?,?,?)",(r["id"],kind,msg,now()))
    c.commit(); c.close()

def summary():
    c=connect(); t=date.today().isoformat()
    def n(q,p=()): return c.execute(q,p).fetchone()[0]
    arrears=c.execute("SELECT COALESCE(SUM(i.amount-COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.invoice_id=i.id),0)),0) FROM invoices i WHERE i.due_date<?",(t,)).fetchone()[0]
    low=c.execute("SELECT COUNT(*) FROM stock_items s WHERE (SELECT COALESCE(SUM(CASE WHEN m.kind='IN' THEN m.quantity ELSE -m.quantity END),0) FROM stock_movements m WHERE m.item_id=s.id)<=s.reorder_level").fetchone()[0]
    out={"tasks":{"due_today":n("SELECT COUNT(*) FROM tasks WHERE due_date=? AND status!='COMPLETED'",(t,)),"overdue":n("SELECT COUNT(*) FROM tasks WHERE due_date<? AND status!='COMPLETED'",(t,)),"open":n("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('COMPLETED','CANCELLED')"),"completed_7d":n("SELECT COUNT(*) FROM tasks WHERE status='COMPLETED' AND completed_at>=?",((date.today()-timedelta(days=7)).isoformat(),))},"property":{"tenants":n("SELECT COUNT(*) FROM tenants WHERE status='ACTIVE'"),"vacant_units":n("SELECT COUNT(*) FROM units WHERE status='VACANT'"),"arrears":round(arrears,2)},"operations":{"maintenance_open":n("SELECT COUNT(*) FROM maintenance WHERE status NOT IN ('CLOSED','CANCELLED')"),"incidents_open":n("SELECT COUNT(*) FROM incidents WHERE status!='CLOSED'"),"low_stock":low},"reminders_pending":n("SELECT COUNT(*) FROM reminders WHERE delivered=0")}
    c.close(); return out

def task_rows(c,qs):
    where=[]; p=[]
    if qs.get("status",[""])[0]: where.append("status=?"); p.append(qs["status"][0].upper())
    if qs.get("area",[""])[0]: where.append("area=?"); p.append(qs["area"][0])
    if qs.get("q",[""])[0]: where.append("(title LIKE ? OR responsible LIKE ? OR area LIKE ?)"); p += ["%"+qs["q"][0]+"%"]*3
    sql="SELECT * FROM tasks"+(" WHERE "+" AND ".join(where) if where else "")+" ORDER BY due_date,status LIMIT 300"
    rows=[]; today=date.today().isoformat()
    for r in c.execute(sql,p):
        x=dict(r); x["overdue"]=x["status"] not in ("COMPLETED","CANCELLED") and x["due_date"]<today; rows.append(x)
    return rows

def page():
 return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ADMIN</title><style>*{box-sizing:border-box}body{margin:0;font:14px system-ui;background:#f5f6f4;color:#18251d}header{background:#214f3a;color:white;padding:18px}main{max-width:1200px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.card,.panel{background:white;border:1px solid #dfe4df;border-radius:10px;padding:14px}.n{font-size:25px;font-weight:700}.muted{color:#66736b}.danger{color:#a52c23}.ok{color:#247044}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px;border-bottom:1px solid #e6e9e6}button,input,select{padding:8px;border:1px solid #ccd4ce;border-radius:7px;font:inherit}button{background:#214f3a;color:white;border:0}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.pill{padding:3px 8px;border-radius:99px;background:#eef2ee}form{display:flex;gap:8px;flex-wrap:wrap}.hidden{display:none}</style></head><body><header><b>ADMIN</b><div>Farm &amp; Property Management · System of Record</div></header><main><div id="app">Loading…</div></main><script>
const $=x=>document.getElementById(x);async function api(u,o){let r=await fetch(u,o);if(r.status===401){location='/login';return null}let x=await r.json();if(!r.ok)throw Error(x.error||'Request failed');return x}
async function load(){let s=await api('/api/v1/summary'),t=await api('/api/v1/tasks'),m=await api('/api/v1/reminders');$('app').innerHTML=`<div class="grid">${card(s.tasks.due_today,'Due today','ok')}${card(s.tasks.overdue,'Overdue','danger')}${card(s.tasks.open,'Open tasks','')}${card(s.property.vacant_units,'Vacant units','')}${card('M '+s.property.arrears.toLocaleString(),'Arrears','danger')}${card(s.operations.maintenance_open,'Open maintenance','')}${card(s.operations.incidents_open,'Open incidents','danger')}${card(s.operations.low_stock,'Low stock','')}</div><div class="panel" style="margin-top:16px"><h2>Task Register</h2><div class="bar"><input id="q" placeholder="Search…"><select id="st"><option value="">All statuses</option>${['PENDING','ASSIGNED','IN_PROGRESS','BLOCKED','SUBMITTED','VERIFICATION_REQUIRED','COMPLETED','CANCELLED'].map(x=>`<option>${x}</option>`).join('')}</select><button onclick="refreshTasks()">Filter</button><button onclick="newTask()">+ Task</button><button onclick="logout()">Sign out</button></div><div style="overflow:auto"><table><thead><tr><th>Task</th><th>Area</th><th>Responsible</th><th>Due</th><th>Status</th><th></th></tr></thead><tbody id="tasks">${taskRows(t)}</tbody></table></div></div><div class="panel"><h2>Pending reminders</h2>${m.length?'<ul>'+m.map(x=>`<li>${esc(x.message)}</li>`).join('')+'</ul>':'<span class="muted">None</span>'}</div>`}
function card(n,l,c){return `<div class="card ${c}"><div class="n">${n}</div><div class="muted">${l}</div></div>`}function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}function taskRows(a){return a.map(x=>`<tr><td>${esc(x.title)} ${x.overdue?'<span class="pill danger">OVERDUE</span>':''}</td><td>${esc(x.area)}</td><td>${esc(x.responsible)}</td><td>${x.due_date}</td><td>${x.status}</td><td>${x.status==='PENDING'?`<button onclick="transition(${x.id},'assign')">Assign</button>`:x.status==='ASSIGNED'?`<button onclick="transition(${x.id},'start')">Start</button>`:x.status==='IN_PROGRESS'?`<button onclick="transition(${x.id},'submit')">Submit</button>`:x.status==='SUBMITTED'?`<button onclick="transition(${x.id},'verify')">Verify</button>`:x.status==='VERIFICATION_REQUIRED'?`<button onclick="transition(${x.id},'complete')">Complete</button>`:''}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">No tasks.</td></tr>'}
async function refreshTasks(){let t=await api('/api/v1/tasks?status='+encodeURIComponent($('st').value)+'&q='+encodeURIComponent($('q').value));$('tasks').innerHTML=taskRows(t)}async function transition(id,a){await api('/api/v1/tasks/'+id+'/'+a,{method:'POST'});load()}async function newTask(){let title=prompt('Task title');if(!title)return;let due=prompt('Due date YYYY-MM-DD',new Date().toISOString().slice(0,10));await api('/api/v1/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,due_date:due,priority:'MEDIUM',responsible:'Administrative Officer'})});load()}async function logout(){await api('/api/v1/auth/logout',{method:'POST'});location='/login'}load().catch(e=>$('app').innerText=e.message);</script></body></html>'''
def login_page(): return '''<!doctype html><html><body style="font:16px system-ui;max-width:420px;margin:10vh auto;padding:20px"><h1>ADMIN</h1><p>Sign in to the Farm & Property Management system.</p><form method="post" action="/login"><input name="username" value="admin" required placeholder="Username" style="padding:10px;width:100%;margin:5px 0"><input name="password" type="password" required placeholder="Password" style="padding:10px;width:100%;margin:5px 0"><button style="padding:10px;width:100%">Sign in</button></form></body></html>'''

def transition(c,actor,tid,action):
    r=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
    if not r: raise ValueError("Task not found")
    allowed={"PENDING":("assign","ASSIGNED"),"ASSIGNED":("start","IN_PROGRESS"),"IN_PROGRESS":("submit","SUBMITTED"),"SUBMITTED":("verify","VERIFICATION_REQUIRED"),"VERIFICATION_REQUIRED":("complete","COMPLETED")}
    cur=allowed.get(r["status"])
    if not cur or cur[0]!=action: raise ValueError("Invalid task transition")
    new=cur[1]; completed=now() if new=="COMPLETED" else None
    c.execute("UPDATE tasks SET status=?,updated_at=?,completed_at=COALESCE(?,completed_at) WHERE id=?",(new,now(),completed,tid)); audit(c,actor,"TASK_"+action.upper(),"task",tid,dict(r),dict(c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()))

class H(BaseHTTPRequestHandler):
    def sendj(self,code,obj,headers=None):
        b=json.dumps(obj).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); [self.send_header(k,v) for k,v in (headers or {}).items()]; self.end_headers(); self.wfile.write(b)
    def html(self,code,s):
        b=s.encode(); self.send_response(code); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def user(self):
        token=self.headers.get('Cookie','').replace(COOKIE+'=','').split(';')[0]
        with SESSIONS_LOCK:
            s=SESSIONS.get(token)
            if s and s[1]>time.time(): return s[0]
            if token: SESSIONS.pop(token,None)
        return None
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        p=urlparse(self.path); path=p.path
        if path=='/login': return self.html(200,login_page())
        if path=='/api/v1/health': return self.sendj(200,{"ok":True,"time":now()})
        if not self.user(): return self.sendj(401,{"error":"authentication required"}) if path.startswith('/api/') else self.html(302,'<script>location="/login"</script>')
        if path=='/': return self.html(200,page())
        if path=='/api/v1/summary': return self.sendj(200,summary())
        c=connect()
        try:
            if path=='/api/v1/tasks': return self.sendj(200,task_rows(c,parse_qs(p.query)))
            if path=='/api/v1/reminders': return self.sendj(200,[dict(x) for x in c.execute("SELECT * FROM reminders WHERE delivered=0 ORDER BY due_at LIMIT 100")])
            if path=='/api/v1/integrations': return self.sendj(200,[{"kind":x["kind"],"provider":x["provider"],"status":x["status"]} for x in c.execute("SELECT * FROM integration_settings")])
            if path=='/api/v1/tenants': return self.sendj(200,[dict(x) for x in c.execute("SELECT * FROM tenants ORDER BY name")])
            if path=='/api/v1/properties': return self.sendj(200,[dict(x) for x in c.execute("SELECT * FROM properties ORDER BY name")])
            return self.sendj(404,{"error":"not found"})
        finally:c.close()
    def do_POST(self):
        path=urlparse(self.path).path
        if path=='/login':
            n=int(self.headers.get('Content-Length','0')); data=parse_qs(self.rfile.read(n).decode()); u=data.get('username',[''])[0]; p=data.get('password',[''])[0]
            c=connect(); r=c.execute("SELECT * FROM users WHERE username=? AND active=1",(u,)).fetchone(); c.close()
            if not r or not password_ok(p,r['password_hash']): return self.html(401,'Invalid credentials')
            token=secrets.token_urlsafe(32)
            with SESSIONS_LOCK: SESSIONS[token]=(u,time.time()+SESSION_TTL)
            return self.html(302,'<script>location="/"</script>')
        if not self.user(): return self.sendj(401,{"error":"authentication required"})
        try:
            c=connect(); b=self.body() if self.headers.get('Content-Length') else {}
            if path=='/api/v1/auth/logout':
                token=self.headers.get('Cookie','').replace(COOKIE+'=','').split(';')[0]
                with SESSIONS_LOCK: SESSIONS.pop(token,None)
                return self.sendj(200,{"ok":True})
            if path=='/api/v1/tasks':
                title=str(b.get('title','')).strip()
                if not title: raise ValueError('title is required')
                due=b.get('due_date',date.today().isoformat()); priority=str(b.get('priority','MEDIUM')).upper(); responsible=str(b.get('responsible','Administrative Officer')).strip()
                if priority not in PRIORITIES: raise ValueError('invalid priority')
                cur=c.execute("INSERT INTO tasks(title,area,responsible,priority,due_date,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(title,b.get('area','General'),responsible,priority,due,'PENDING',now(),now())); audit(c,self.user(),'TASK_CREATED','task',cur.lastrowid,None,b); c.commit(); return self.sendj(201,{"id":cur.lastrowid})
            parts=path.strip('/').split('/')
            if len(parts)==4 and parts[0:3]==['api','v1','tasks']:
                tid=int(parts[3]); transition(c,self.user(),tid,parts[3] if False else '')
            if len(parts)==5 and parts[:3]==['api','v1','tasks']:
                transition(c,self.user(),int(parts[3]),parts[4]); c.commit(); return self.sendj(200,{"ok":True})
            return self.sendj(404,{"error":"not found"})
        except Exception as e:
            try:c.rollback()
            except Exception:pass
            return self.sendj(400,{"error":str(e)})
        finally:c.close()
    def log_message(self,*a): pass

def scheduler():
    while True:
        try: materialize()
        except Exception as e: print('scheduler:',e)
        time.sleep(60)

if __name__=='__main__':
    init_db(); materialize(); threading.Thread(target=scheduler,daemon=True).start(); print(f'ADMIN running on http://127.0.0.1:{PORT}'); ThreadingHTTPServer((HOST,PORT),H).serve_forever()
