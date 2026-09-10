#!/usr/bin/env python3
"""Runnable ADMIN application.

The local baseline uses only Python's standard library. SQLite is the persistence
adapter for a zero-dependency install; the API boundary is stable for the planned
PostgreSQL adapter. External providers are configuration data, never hard-coded.
"""
import base64, hashlib, hmac, json, os, secrets, sqlite3, threading, time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST=os.getenv('ADMIN_HOST','0.0.0.0'); PORT=int(os.getenv('ADMIN_PORT','8000')); DB=os.getenv('ADMIN_DB','admin.db')
STATUSES=('PENDING','ASSIGNED','IN_PROGRESS','BLOCKED','SUBMITTED','VERIFICATION_REQUIRED','COMPLETED','CANCELLED')
PRIORITIES=('LOW','MEDIUM','HIGH','URGENT')
TEMPLATES=[
('Farm Operations','Coordinate crop & livestock activities','daily','Farm Supervisor / Caretakers','HIGH'),
('Livestock','Livestock feeding, watering & health checks','daily','Caretakers / Workers','HIGH'),
('Farm Workers','Attendance, duty allocation & supervision','daily','Supervisor','HIGH'),
('Daily Coordination','Morning / midday / end-of-day coordination','daily','Administrative Officer','HIGH'),
('Maintenance','Log and coordinate repairs and preventative maintenance','daily','Caretakers / Contractors','MEDIUM'),
('Records','Maintain registers, logs, invoices and supporting documents','daily','Administrative Officer','MEDIUM'),
('Weekly Planning','Review outstanding work and allocate priorities','weekly','Administrative Officer','HIGH'),
('Property Management','Property inspections and condition monitoring','weekly','Caretakers','MEDIUM'),
('Reporting','Weekly performance review and management report','weekly','Administrative Officer','HIGH'),
('Accommodation','Occupancy, vacancies, leases and occupant records review','monthly','Administrative Officer','MEDIUM'),
('Stock Control','Stock count and variance review','monthly','Responsible Staff','MEDIUM'),
('Reporting','Monthly management report','monthly','Administrative Officer','HIGH'),
('Assets','Asset register audit','quarterly','Administrative Officer','LOW')]

def now(): return datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
def db():
 c=sqlite3.connect(DB,timeout=20); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=WAL'); return c
def phash(p,s=None):
 s=s or secrets.token_bytes(16); return base64.urlsafe_b64encode(s).decode()+'$'+base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256',p.encode(),s,210000)).decode()
def pcheck(p,v):
 try:
  a,b=v.split('$',1); s=base64.urlsafe_b64decode(a); return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),s,210000),base64.urlsafe_b64decode(b))
 except Exception:return False
def audit(c,actor,action,entity,eid,before=None,after=None):
 c.execute('INSERT INTO audit_log(actor,action,entity,entity_id,before_json,after_json,created_at) VALUES(?,?,?,?,?,?,?)',(actor,action,entity,str(eid),json.dumps(before,sort_keys=True) if before else None,json.dumps(after,sort_keys=True) if after else None,now()))

def init():
 c=db(); c.executescript('''
 CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS task_templates(id INTEGER PRIMARY KEY AUTOINCREMENT,area TEXT NOT NULL,title TEXT NOT NULL,cadence TEXT NOT NULL,responsible TEXT NOT NULL,priority TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,UNIQUE(area,title));
 CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,template_id INTEGER,title TEXT NOT NULL,area TEXT,responsible TEXT,priority TEXT NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',note TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,completed_at TEXT,FOREIGN KEY(template_id) REFERENCES task_templates(id),UNIQUE(template_id,due_date));
 CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id INTEGER NOT NULL,kind TEXT NOT NULL,message TEXT NOT NULL,due_at TEXT NOT NULL,delivered INTEGER NOT NULL DEFAULT 0,UNIQUE(task_id,kind));
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
 ''')
 if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
  pw=os.getenv('ADMIN_PASSWORD') or secrets.token_urlsafe(24); c.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES('admin',?,'SYSTEM_ADMIN',?)",(phash(pw),now())); print('ADMIN bootstrap password:', 'configured by ADMIN_PASSWORD' if os.getenv('ADMIN_PASSWORD') else pw)
 for r in TEMPLATES:c.execute('INSERT OR IGNORE INTO task_templates(area,title,cadence,responsible,priority) VALUES(?,?,?,?,?)',r)
 c.commit(); c.close()

def materialize():
 c=db(); ts=list(c.execute('SELECT * FROM task_templates WHERE active=1')); today=date.today(); start=today-timedelta(days=4); end=today+timedelta(days=14)
 for t in ts:
  d=start
  while d<=end:
   due=t['cadence']=='daily' or (t['cadence']=='weekly' and d.weekday()==0) or (t['cadence']=='monthly' and d.day==1) or (t['cadence']=='quarterly' and d.day==1 and d.month in (1,4,7,10))
   if due:c.execute('INSERT OR IGNORE INTO tasks(template_id,title,area,responsible,priority,due_date,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(t['id'],t['title'],t['area'],t['responsible'],t['priority'],d.isoformat(),'PENDING',now(),now()))
   d+=timedelta(days=1)
 today_s=today.isoformat(); rows=list(c.execute("SELECT id,title,due_date FROM tasks WHERE status NOT IN ('COMPLETED','CANCELLED') AND due_date<=?",(today_s,)))
 for r in rows:
  kind='due' if r['due_date']==today_s else 'overdue'; msg=('Due today: ' if kind=='due' else 'OVERDUE: ')+r['title']; c.execute('INSERT OR IGNORE INTO reminders(task_id,kind,message,due_at) VALUES(?,?,?,?)',(r['id'],kind,msg,now()))
 c.commit(); c.close()

def summary():
 c=db(); t=date.today().isoformat(); q=lambda s,p=():c.execute(s,p).fetchone()[0]
 arrears=c.execute("SELECT COALESCE(SUM(i.amount-COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.invoice_id=i.id),0)),0) FROM invoices i WHERE i.due_date<?",(t,)).fetchone()[0]
 low=q("SELECT COUNT(*) FROM stock_items s WHERE (SELECT COALESCE(SUM(CASE WHEN m.kind='IN' THEN m.quantity ELSE -m.quantity END),0) FROM stock_movements m WHERE m.item_id=s.id)<=s.reorder_level")
 x={'tasks':{'due_today':q("SELECT COUNT(*) FROM tasks WHERE due_date=? AND status NOT IN ('COMPLETED','CANCELLED')",(t,)),'overdue':q("SELECT COUNT(*) FROM tasks WHERE due_date<? AND status NOT IN ('COMPLETED','CANCELLED')",(t,)),'open':q("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('COMPLETED','CANCELLED')"),'completed_7d':q("SELECT COUNT(*) FROM tasks WHERE status='COMPLETED' AND completed_at>=?",((date.today()-timedelta(days=7)).isoformat(),))},'property':{'tenants':q("SELECT COUNT(*) FROM tenants WHERE status='ACTIVE'"),'vacant_units':q("SELECT COUNT(*) FROM units WHERE status='VACANT'"),'arrears':round(arrears,2)},'operations':{'maintenance_open':q("SELECT COUNT(*) FROM maintenance WHERE status NOT IN ('CLOSED','CANCELLED')"),'incidents_open':q("SELECT COUNT(*) FROM incidents WHERE status!='CLOSED'"),'low_stock':low},'reminders_pending':q("SELECT COUNT(*) FROM reminders WHERE delivered=0")}; c.close(); return x

def tasks(c,qs):
 w=[];p=[]
 for key,col in [('status','status'),('area','area')]:
  v=qs.get(key,[''])[0]
  if v:w.append(col+'=?');p.append(v.upper() if key=='status' else v)
 v=qs.get('q',[''])[0]
 if v:w.append('(title LIKE ? OR responsible LIKE ? OR area LIKE ?)');p += ['%'+v+'%']*3
 sql='SELECT * FROM tasks'+((' WHERE '+' AND '.join(w)) if w else '')+' ORDER BY due_date,status LIMIT 300'; today=date.today().isoformat(); out=[]
 for r in c.execute(sql,p):x=dict(r);x['overdue']=x['status'] not in ('COMPLETED','CANCELLED') and x['due_date']<today;out.append(x)
 return out

def page():
 return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ADMIN</title><style>*{box-sizing:border-box}body{margin:0;font:14px system-ui;background:#f4f6f3;color:#17241c}header{background:#214f3a;color:#fff;padding:18px}main{max-width:1200px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px}.card,.panel{background:#fff;border:1px solid #dfe5df;border-radius:10px;padding:14px}.n{font-size:25px;font-weight:700}.muted{color:#68756d}.danger{color:#a42e24}.ok{color:#277044}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}input,select,button{padding:8px;border:1px solid #cbd4cd;border-radius:7px;font:inherit}button{background:#214f3a;color:#fff;border:0;cursor:pointer}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px;border-bottom:1px solid #e7ebe7}.pill{padding:3px 7px;border-radius:99px;background:#eef2ee}</style></head><body><header><b>ADMIN</b><div>Farm &amp; Property Management · System of Record</div></header><main><div id="app">Loading…</div></main><script>
const $=id=>document.getElementById(id);async function api(u,o){let r=await fetch(u,o);if(r.status===401){location.reload();return null}let x=await r.json();if(!r.ok)throw Error(x.error||'Request failed');return x}
const esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function card(n,l,c){return `<div class="card ${c}"><div class="n">${n}</div><div class="muted">${l}</div></div>`}
function rows(a){return a.map(x=>`<tr><td>${esc(x.title)} ${x.overdue?'<span class="pill danger">OVERDUE</span>':''}</td><td>${esc(x.area)}</td><td>${esc(x.responsible)}</td><td>${x.due_date}</td><td>${x.status}</td><td>${x.status==='PENDING'?`<button onclick="go(${x.id},'assign')">Assign</button>`:x.status==='ASSIGNED'?`<button onclick="go(${x.id},'start')">Start</button>`:x.status==='IN_PROGRESS'?`<button onclick="go(${x.id},'submit')">Submit</button>`:x.status==='SUBMITTED'?`<button onclick="go(${x.id},'verify')">Verify</button>`:x.status==='VERIFICATION_REQUIRED'?`<button onclick="go(${x.id},'complete')">Complete</button>`:''}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">No tasks.</td></tr>'}
async function load(){let s=await api('/api/v1/summary'),t=await api('/api/v1/tasks'),m=await api('/api/v1/reminders');$('app').innerHTML=`<div class="grid">${card(s.tasks.due_today,'Due today','ok')}${card(s.tasks.overdue,'Overdue','danger')}${card(s.tasks.open,'Open tasks','')}${card(s.property.vacant_units,'Vacant units','')}${card('M '+s.property.arrears.toLocaleString(),'Arrears','danger')}${card(s.operations.maintenance_open,'Open maintenance','')}${card(s.operations.incidents_open,'Open incidents','danger')}${card(s.operations.low_stock,'Low stock','')}</div><div class="panel" style="margin-top:16px"><h2>Task Register</h2><div class="bar"><input id="q" placeholder="Search task/person/area"><select id="st"><option value="">All statuses</option>${['PENDING','ASSIGNED','IN_PROGRESS','BLOCKED','SUBMITTED','VERIFICATION_REQUIRED','COMPLETED','CANCELLED'].map(x=>`<option>${x}</option>`).join('')}</select><button onclick="filterTasks()">Filter</button><button onclick="addTask()">+ Task</button></div><div style="overflow:auto"><table><thead><tr><th>Task</th><th>Area</th><th>Responsible</th><th>Due</th><th>Status</th><th></th></tr></thead><tbody id="taskRows">${rows(t)}</tbody></table></div></div><div class="panel"><h2>Pending reminders</h2>${m.length?'<ul>'+m.map(x=>`<li>${esc(x.message)}</li>`).join('')+'</ul>':'<span class="muted">None</span>'}</div>`}
async function filterTasks(){let a=await api('/api/v1/tasks?status='+encodeURIComponent($('st').value)+'&q='+encodeURIComponent($('q').value));$('taskRows').innerHTML=rows(a)}async function go(id,a){await api('/api/v1/tasks/'+id+'/'+a,{method:'POST'});load()}async function addTask(){let title=prompt('Task title');if(!title)return;let due=prompt('Due date YYYY-MM-DD',new Date().toISOString().slice(0,10));if(!due)return;await api('/api/v1/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,due_date:due,area:'General',responsible:'Administrative Officer',priority:'MEDIUM'})});load()}load().catch(e=>$('app').innerText=e.message);
</script></body></html>'''

def auth(self):
 h=self.headers.get('Authorization','')
 if not h.startswith('Basic '):return None
 try:u,p=base64.b64decode(h[6:]).decode().split(':',1)
 except Exception:return None
 c=db();r=c.execute('SELECT * FROM users WHERE username=? AND active=1',(u,)).fetchone();c.close();return u if r and pcheck(p,r['password_hash']) else None

class H(BaseHTTPRequestHandler):
 def j(self,code,obj,extra=None):
  b=json.dumps(obj).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');
  if extra:
   for k,v in extra.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(b)
 def h(self,code,s,extra=None):
  b=s.encode();self.send_response(code);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));
  if extra:
   for k,v in extra.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(b)
 def body(self):n=int(self.headers.get('Content-Length','0'));return json.loads(self.rfile.read(n) or b'{}')
 def user_or_401(self):
  u=auth(self)
  if not u:self.j(401,{'error':'authentication required'},{'WWW-Authenticate':'Basic realm="ADMIN"'});return None
  return u
 def do_GET(self):
  p=urlparse(self.path); path=p.path
  if path=='/api/v1/health':return self.j(200,{'ok':True,'time':now()})
  u=self.user_or_401()
  if not u:return
  if path=='/':return self.h(200,page())
  c=db()
  try:
   if path=='/api/v1/summary':return self.j(200,summary())
   if path=='/api/v1/tasks':return self.j(200,tasks(c,parse_qs(p.query)))
   if path=='/api/v1/reminders':return self.j(200,[dict(x) for x in c.execute('SELECT * FROM reminders WHERE delivered=0 ORDER BY due_at LIMIT 100')])
   if path=='/api/v1/tenants':return self.j(200,[dict(x) for x in c.execute('SELECT * FROM tenants ORDER BY name')])
   if path=='/api/v1/properties':return self.j(200,[dict(x) for x in c.execute('SELECT * FROM properties ORDER BY name')])
   if path=='/api/v1/integrations':return self.j(200,[{'kind':x['kind'],'provider':x['provider'],'status':x['status']} for x in c.execute('SELECT * FROM integration_settings ORDER BY kind')])
   if path=='/api/v1/audit':return self.j(200,[dict(x) for x in c.execute('SELECT id,actor,action,entity,entity_id,created_at FROM audit_log ORDER BY id DESC LIMIT 200')])
   return self.j(404,{'error':'not found'})
  finally:c.close()
 def do_POST(self):
  u=self.user_or_401()
  if not u:return
  path=urlparse(self.path).path
  try:
   c=db(); b=self.body() if self.headers.get('Content-Length') else {}
   if path=='/api/v1/tasks':
    title=str(b.get('title','')).strip();due=str(b.get('due_date',date.today().isoformat()));prio=str(b.get('priority','MEDIUM')).upper()
    if not title:raise ValueError('title is required')
    if prio not in PRIORITIES:raise ValueError('invalid priority')
    try:date.fromisoformat(due)
    except ValueError:raise ValueError('due_date must be YYYY-MM-DD')
    cur=c.execute("INSERT INTO tasks(title,area,responsible,priority,due_date,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(title,str(b.get('area','General')),str(b.get('responsible','Administrative Officer')),prio,due,'PENDING',now(),now()));audit(c,u,'TASK_CREATED','task',cur.lastrowid,None,b);c.commit();return self.j(201,{'id':cur.lastrowid})
   parts=path.strip('/').split('/')
   if len(parts)==5 and parts[:3]==['api','v1','tasks']:
    tid=int(parts[3]); action=parts[4]; r=c.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
    if not r:raise ValueError('task not found')
    allowed={'PENDING':('assign','ASSIGNED'),'ASSIGNED':('start','IN_PROGRESS'),'IN_PROGRESS':('submit','SUBMITTED'),'SUBMITTED':('verify','VERIFICATION_REQUIRED'),'VERIFICATION_REQUIRED':('complete','COMPLETED')}.get(r['status'])
    if not allowed or action!=allowed[0]:raise ValueError('invalid task transition')
    new=allowed[1];done=now() if new=='COMPLETED' else None;c.execute('UPDATE tasks SET status=?,updated_at=?,completed_at=COALESCE(?,completed_at) WHERE id=?',(new,now(),done,tid));audit(c,u,'TASK_'+action.upper(),'task',tid,dict(r),{'status':new});c.execute("UPDATE reminders SET delivered=1 WHERE task_id=? AND kind='due'",(tid,));c.commit();return self.j(200,{'ok':True,'status':new})
   return self.j(404,{'error':'not found'})
  except Exception as e:
   try:c.rollback();c.close()
   except Exception:pass
   return self.j(400,{'error':str(e)})
 def log_message(self,*a):pass

def worker():
 while True:
  try:materialize()
  except Exception as e:print('scheduler:',e)
  time.sleep(60)

if __name__=='__main__':
 init();materialize();threading.Thread(target=worker,daemon=True).start();print(f'ADMIN running on http://127.0.0.1:{PORT}');ThreadingHTTPServer((HOST,PORT),H).serve_forever()
