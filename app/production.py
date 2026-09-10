#!/usr/bin/env python3
"""ADMIN production application layer.

Standard-library only so the repository remains runnable. SQLite is the local
adapter; the business/API boundaries are intentionally small and replaceable by
PostgreSQL in deployment. No external provider credentials are embedded.
"""
import base64, hashlib, hmac, json, os, secrets, sqlite3, threading, time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST=os.getenv('ADMIN_HOST','0.0.0.0'); PORT=int(os.getenv('ADMIN_PORT','8000')); DB=os.getenv('ADMIN_DB','admin.db')
ROLES=('SYSTEM_ADMIN','ADMIN_OFFICER','HOSS','FINANCE','SUPERVISOR','WORKER','CONTRACTOR','MANAGEMENT')
TASK_STATUS=('PENDING','ASSIGNED','IN_PROGRESS','BLOCKED','SUBMITTED','VERIFICATION_REQUIRED','COMPLETED','CANCELLED')
MAINT_STATUS=('REPORTED','TRIAGED','ASSIGNED','IN_PROGRESS','COMPLETED','VERIFIED','CLOSED','CANCELLED')
SEVERITY=('LOW','MEDIUM','HIGH','CRITICAL')
PRIORITIES=('LOW','MEDIUM','HIGH','URGENT')
TEMPLATES=[
('Farm Operations','Coordinate crop & livestock activities','daily','Farm Supervisor / Caretakers','HIGH'),('Livestock','Livestock feeding, watering & health checks','daily','Caretakers / Workers','HIGH'),('Farm Workers','Attendance, duty allocation & supervision','daily','Supervisor','HIGH'),('Daily Coordination','Morning / midday / end-of-day coordination','daily','Administrative Officer','HIGH'),('Maintenance','Log and coordinate repairs and preventative maintenance','daily','Caretakers / Contractors','MEDIUM'),('Records','Maintain registers, logs, invoices and supporting documents','daily','Administrative Officer','MEDIUM'),('Weekly Planning','Review outstanding work and allocate priorities','weekly','Administrative Officer','HIGH'),('Property Management','Property inspections and condition monitoring','weekly','Caretakers','MEDIUM'),('Reporting','Weekly performance review and management report','weekly','Administrative Officer','HIGH'),('Accommodation','Occupancy, vacancies, leases and occupant records review','monthly','Administrative Officer','MEDIUM'),('Stock Control','Stock count and variance review','monthly','Responsible Staff','MEDIUM'),('Reporting','Monthly management report','monthly','Administrative Officer','HIGH'),('Assets','Asset register audit','quarterly','Administrative Officer','LOW')]

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
 c.execute('INSERT INTO audit_log(actor,action,entity,entity_id,before_json,after_json,created_at) VALUES(?,?,?,?,?,?,?)',(actor,action,entity,str(eid),json.dumps(before,sort_keys=True) if before is not None else None,json.dumps(after,sort_keys=True) if after is not None else None,now()))

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
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_id INTEGER NOT NULL,amount REAL NOT NULL,reference TEXT NOT NULL UNIQUE,received_at TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(invoice_id) REFERENCES invoices(id));
CREATE TABLE IF NOT EXISTS maintenance(id INTEGER PRIMARY KEY AUTOINCREMENT,tenant_id INTEGER,description TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'REPORTED',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(tenant_id) REFERENCES tenants(id));
CREATE TABLE IF NOT EXISTS stock_items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT,reorder_level REAL NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER NOT NULL,quantity REAL NOT NULL,kind TEXT NOT NULL,reference TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,FOREIGN KEY(item_id) REFERENCES stock_items(id));
CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT,location TEXT,status TEXT NOT NULL DEFAULT 'IN_USE',last_audit TEXT);
CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT NOT NULL,description TEXT NOT NULL,severity TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'REPORTED',reported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS integration_settings(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT UNIQUE NOT NULL,provider TEXT,status TEXT NOT NULL DEFAULT 'NOT_CONFIGURED',config_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,entity TEXT NOT NULL,entity_id TEXT,before_json TEXT,after_json TEXT,created_at TEXT NOT NULL);
''')
 if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
  pw=os.getenv('ADMIN_PASSWORD') or secrets.token_urlsafe(24); c.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES('admin',?,'SYSTEM_ADMIN',?)",(phash(pw),now())); print('ADMIN bootstrap password:', 'configured by ADMIN_PASSWORD' if os.getenv('ADMIN_PASSWORD') else pw)
 for r in TEMPLATES:c.execute('INSERT OR IGNORE INTO task_templates(area,title,cadence,responsible,priority) VALUES(?,?,?,?,?)',r)
 for kind in ('WHATSAPP','EMAIL','SMS','MOBILE_MONEY','E_SIGNATURE','OBJECT_STORAGE','ACCOUNTING','HR_PAYROLL'):
  c.execute('INSERT OR IGNORE INTO integration_settings(kind,provider,status,config_json,updated_at) VALUES(?,?,?,?,?)',(kind,'','NOT_CONFIGURED','{}',now()))
 c.commit(); c.close()

def materialize():
 c=db(); today=date.today(); ts=list(c.execute('SELECT * FROM task_templates WHERE active=1'))
 for t in ts:
  d=today-timedelta(days=4)
  while d<=today+timedelta(days=14):
   due=t['cadence']=='daily' or (t['cadence']=='weekly' and d.weekday()==0) or (t['cadence']=='monthly' and d.day==1) or (t['cadence']=='quarterly' and d.day==1 and d.month in (1,4,7,10))
   if due:c.execute('INSERT OR IGNORE INTO tasks(template_id,title,area,responsible,priority,due_date,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(t['id'],t['title'],t['area'],t['responsible'],t['priority'],d.isoformat(),'PENDING',now(),now()))
   d+=timedelta(days=1)
 today_s=today.isoformat()
 for r in c.execute("SELECT id,title,due_date FROM tasks WHERE status NOT IN ('COMPLETED','CANCELLED') AND due_date<=?",(today_s,)):
  kind='due' if r['due_date']==today_s else 'overdue'; msg=('Due today: ' if kind=='due' else 'OVERDUE: ')+r['title']; c.execute('INSERT OR IGNORE INTO reminders(task_id,kind,message,due_at) VALUES(?,?,?,?)',(r['id'],kind,msg,now()))
 c.commit(); c.close()

def summary():
 c=db(); t=date.today().isoformat(); q=lambda s,p=():c.execute(s,p).fetchone()[0]
 arrears=c.execute("SELECT COALESCE(SUM(i.amount-COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.invoice_id=i.id),0)),0) FROM invoices i WHERE i.due_date<?",(t,)).fetchone()[0]
 low=q("SELECT COUNT(*) FROM stock_items s WHERE (SELECT COALESCE(SUM(CASE WHEN m.kind='IN' THEN m.quantity ELSE -m.quantity END),0) FROM stock_movements m WHERE m.item_id=s.id)<=s.reorder_level")
 out={'tasks':{'due_today':q("SELECT COUNT(*) FROM tasks WHERE due_date=? AND status NOT IN ('COMPLETED','CANCELLED')",(t,)),'overdue':q("SELECT COUNT(*) FROM tasks WHERE due_date<? AND status NOT IN ('COMPLETED','CANCELLED')",(t,)),'open':q("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('COMPLETED','CANCELLED')"),'completed_7d':q("SELECT COUNT(*) FROM tasks WHERE status='COMPLETED' AND completed_at>=?",((date.today()-timedelta(days=7)).isoformat(),))},'property':{'tenants':q("SELECT COUNT(*) FROM tenants WHERE status='ACTIVE'"),'properties':q('SELECT COUNT(*) FROM properties'),'units':q('SELECT COUNT(*) FROM units'),'vacant_units':q("SELECT COUNT(*) FROM units WHERE status='VACANT'"),'arrears':round(arrears,2)},'operations':{'maintenance_open':q("SELECT COUNT(*) FROM maintenance WHERE status NOT IN ('CLOSED','CANCELLED')"),'incidents_open':q("SELECT COUNT(*) FROM incidents WHERE status!='CLOSED'"),'low_stock':low},'reminders_pending':q('SELECT COUNT(*) FROM reminders WHERE delivered=0')}; c.close(); return out

def auth(self):
 h=self.headers.get('Authorization','')
 if not h.startswith('Basic '):return None
 try:u,p=base64.b64decode(h[6:]).decode().split(':',1)
 except Exception:return None
 c=db(); r=c.execute('SELECT * FROM users WHERE username=? AND active=1',(u,)).fetchone(); c.close(); return (u,r['role']) if r and pcheck(p,r['password_hash']) else None

def body(self):
 n=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(n) if n else b'{}'
 try:return json.loads(raw or b'{}')
 except Exception:raise ValueError('invalid JSON body')
def clean(v): return str(v).strip() if v is not None else ''
def require(b,fields):
 for f in fields:
  if not clean(b.get(f)):raise ValueError(f'{f} is required')
def iso(v,field):
 try:return date.fromisoformat(clean(v)).isoformat()
 except ValueError:raise ValueError(field+' must be YYYY-MM-DD')
def rows(c,table,limit=500):return [dict(x) for x in c.execute(f'SELECT * FROM {table} ORDER BY id DESC LIMIT ?', (limit,))]

class H(BaseHTTPRequestHandler):
 def sendj(self,code,obj,extra=None):
  b=json.dumps(obj,default=str).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store')
  for k,v in (extra or {}).items():self.send_header(k,v)
  self.end_headers(); self.wfile.write(b)
 def sendhtml(self,s):
  b=s.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def guard(self):
  u=auth(self)
  if not u:self.sendj(401,{'error':'authentication required'},{'WWW-Authenticate':'Basic realm="ADMIN"'});return None
  return u
 def do_GET(self):
  p=urlparse(self.path); path=p.path
  if path=='/api/v1/health':return self.sendj(200,{'ok':True,'time':now()})
  u=self.guard()
  if not u:return
  if path=='/':return self.sendhtml(PAGE)
  c=db()
  try:
   if path=='/api/v1/summary':return self.sendj(200,summary())
   if path=='/api/v1/tasks':
    qs=parse_qs(p.query); w=[];args=[]
    if qs.get('status',[''])[0]:w.append('status=?');args.append(qs['status'][0].upper())
    if qs.get('area',[''])[0]:w.append('area=?');args.append(qs['area'][0])
    if qs.get('q',[''])[0]:w.append('(title LIKE ? OR responsible LIKE ? OR area LIKE ?)');args += ['%'+qs['q'][0]+'%']*3
    sql='SELECT * FROM tasks'+((' WHERE '+' AND '.join(w)) if w else '')+' ORDER BY due_date,status LIMIT 500'; today=date.today().isoformat(); out=[]
    for r in c.execute(sql,args):x=dict(r);x['overdue']=x['status'] not in ('COMPLETED','CANCELLED') and x['due_date']<today;out.append(x)
    return self.sendj(200,out)
   if path in ('/api/v1/properties','/api/v1/units','/api/v1/tenants','/api/v1/invoices','/api/v1/payments','/api/v1/maintenance','/api/v1/stock-items','/api/v1/assets','/api/v1/incidents','/api/v1/audit','/api/v1/reminders'):return self.sendj(200,rows(c,{'/api/v1/properties':'properties','/api/v1/units':'units','/api/v1/tenants':'tenants','/api/v1/invoices':'invoices','/api/v1/payments':'payments','/api/v1/maintenance':'maintenance','/api/v1/stock-items':'stock_items','/api/v1/assets':'assets','/api/v1/incidents':'incidents','/api/v1/audit':'audit_log','/api/v1/reminders':'reminders'}[path]))
   if path=='/api/v1/stock':
    return self.sendj(200,[dict(r) | {'balance':c.execute("SELECT COALESCE(SUM(CASE WHEN kind='IN' THEN quantity ELSE -quantity END),0) FROM stock_movements WHERE item_id=?",(r['id'],)).fetchone()[0]} for r in c.execute('SELECT * FROM stock_items WHERE active=1 ORDER BY name')])
   if path=='/api/v1/integrations':return self.sendj(200,[{'kind':r['kind'],'provider':r['provider'],'status':r['status'],'updated_at':r['updated_at']} for r in c.execute('SELECT * FROM integration_settings ORDER BY kind')])
   if path=='/api/v1/templates':return self.sendj(200,rows(c,'task_templates'))
   return self.sendj(404,{'error':'not found'})
  finally:c.close()
 def do_POST(self):
  u=self.guard()
  if not u:return
  path=urlparse(self.path).path; b=body(self); c=db()
  try:
   if path=='/api/v1/tasks':
    require(b,['title']); due=iso(b.get('due_date',date.today().isoformat()),'due_date'); pr=clean(b.get('priority','MEDIUM')).upper()
    if pr not in PRIORITIES:raise ValueError('invalid priority')
    cur=c.execute('INSERT INTO tasks(title,area,responsible,priority,due_date,status,created_at,updated_at,note) VALUES(?,?,?,?,?,?,?,?,?)',(clean(b['title']),clean(b.get('area','General')),clean(b.get('responsible','Administrative Officer')),pr,due,'PENDING',now(),now(),clean(b.get('note')))); audit(c,u[0],'TASK_CREATED','task',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path.startswith('/api/v1/tasks/'):
    parts=path.strip('/').split('/'); tid=int(parts[3]); action=parts[4] if len(parts)>4 else '' ; r=c.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone()
    if not r:raise ValueError('task not found')
    transitions={'PENDING':('assign','ASSIGNED'),'ASSIGNED':('start','IN_PROGRESS'),'IN_PROGRESS':('submit','SUBMITTED'),'SUBMITTED':('verify','VERIFICATION_REQUIRED'),'VERIFICATION_REQUIRED':('complete','COMPLETED')}; expected=transitions.get(r['status'])
    if not expected or action!=expected[0]:raise ValueError('invalid task transition')
    c.execute('UPDATE tasks SET status=?,updated_at=?,completed_at=CASE WHEN ?="COMPLETED" THEN ? ELSE completed_at END WHERE id=?',(expected[1],now(),expected[1],now(),tid));audit(c,u[0],'TASK_'+action.upper(),'task',tid,dict(r),{'status':expected[1]});c.commit();return self.sendj(200,{'ok':True,'status':expected[1]})
   if path=='/api/v1/properties':
    require(b,['name']);cur=c.execute('INSERT INTO properties(name,address,status) VALUES(?,?,?)',(clean(b['name']),clean(b.get('address')),clean(b.get('status','ACTIVE'))));audit(c,u[0],'PROPERTY_CREATED','property',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path=='/api/v1/units':
    require(b,['property_id','name']);cur=c.execute('INSERT INTO units(property_id,name,status,rent_amount) VALUES(?,?,?,?)',(int(b['property_id']),clean(b['name']),clean(b.get('status','VACANT')),float(b.get('rent_amount',0))));audit(c,u[0],'UNIT_CREATED','unit',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path=='/api/v1/tenants':
    require(b,['name']);cur=c.execute('INSERT INTO tenants(name,phone,email,unit_id,status,lease_end,created_at) VALUES(?,?,?,?,?,?,?)',(clean(b['name']),clean(b.get('phone')),clean(b.get('email')),int(b['unit_id']) if b.get('unit_id') else None,clean(b.get('status','ACTIVE')),iso(b['lease_end'],'lease_end') if b.get('lease_end') else None,now()));audit(c,u[0],'TENANT_CREATED','tenant',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path=='/api/v1/invoices':
    require(b,['tenant_id','amount','due_date']);cur=c.execute('INSERT INTO invoices(tenant_id,amount,due_date,created_at) VALUES(?,?,?,?)',(int(b['tenant_id']),float(b['amount']),iso(b['due_date'],'due_date'),now()));audit(c,u[0],'INVOICE_CREATED','invoice',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path.startswith('/api/v1/invoices/') and path.endswith('/payments'):
    iid=int(path.split('/')[4]);require(b,['amount','reference']); ifalse=c.execute('SELECT id,amount FROM invoices WHERE id=?',(iid,)).fetchone()
    if not ifalse:raise ValueError('invoice not found')
    amount=float(b['amount']);
    if amount<=0:raise ValueError('payment amount must be positive')
    paid=c.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE invoice_id=?',(iid,)).fetchone()[0]
    if amount+paid>ifalse['amount']:raise ValueError('payment exceeds invoice balance')
    cur=c.execute('INSERT INTO payments(invoice_id,amount,reference,received_at,created_at) VALUES(?,?,?,?,?)',(iid,amount,clean(b['reference']),clean(b.get('received_at',now())),now()));audit(c,u[0],'PAYMENT_RECORDED','payment',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid,'balance':round(ifalse['amount']-paid-amount,2)})
   if path=='/api/v1/maintenance':
    require(b,['description']);pr=clean(b.get('priority','MEDIUM')).upper();
    if pr not in PRIORITIES:raise ValueError('invalid priority')
    cur=c.execute('INSERT INTO maintenance(tenant_id,description,priority,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',(int(b['tenant_id']) if b.get('tenant_id') else None,clean(b['description']),pr,'REPORTED',now(),now()));audit(c,u[0],'MAINTENANCE_CREATED','maintenance',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path.startswith('/api/v1/maintenance/') and path.endswith('/transition'):
    mid=int(path.split('/')[4]);r=c.execute('SELECT * FROM maintenance WHERE id=?',(mid,)).fetchone();new=clean(b.get('status')).upper();allowed={'REPORTED':('TRIAGED',),'TRIAGED':('ASSIGNED','CANCELLED'),'ASSIGNED':('IN_PROGRESS',),'IN_PROGRESS':('COMPLETED',),'COMPLETED':('VERIFIED',),'VERIFIED':('CLOSED','ASSIGNED')}
    if not r or new not in allowed.get(r['status'],()):raise ValueError('invalid maintenance transition')
    c.execute('UPDATE maintenance SET status=?,updated_at=? WHERE id=?',(new,now(),mid));audit(c,u[0],'MAINTENANCE_TRANSITION','maintenance',mid,dict(r),{'status':new});c.commit();return self.sendj(200,{'status':new})
   if path=='/api/v1/stock-items':
    require(b,['name']);cur=c.execute('INSERT INTO stock_items(name,category,reorder_level) VALUES(?,?,?)',(clean(b['name']),clean(b.get('category')),float(b.get('reorder_level',0))));audit(c,u[0],'STOCK_ITEM_CREATED','stock_item',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path=='/api/v1/stock-movements':
    require(b,['item_id','quantity','kind','reference']);kind=clean(b['kind']).upper();qty=float(b['quantity']);
    if kind not in ('IN','OUT') or qty<=0:raise ValueError('kind must be IN/OUT and quantity must be positive')
    balance=c.execute("SELECT COALESCE(SUM(CASE WHEN kind='IN' THEN quantity ELSE -quantity END),0) FROM stock_movements WHERE item_id=?",(int(b['item_id']),)).fetchone()[0]
    if kind=='OUT' and qty>balance:raise ValueError('stock movement would make balance negative')
    cur=c.execute('INSERT INTO stock_movements(item_id,quantity,kind,reference,created_at) VALUES(?,?,?,?,?)',(int(b['item_id']),qty,kind,clean(b['reference']),now()));audit(c,u[0],'STOCK_MOVEMENT','stock_movement',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid,'balance':balance+(qty if kind=='IN' else -qty)})
   if path=='/api/v1/assets':
    require(b,['name']);cur=c.execute('INSERT INTO assets(name,category,location,status,last_audit) VALUES(?,?,?,?,?)',(clean(b['name']),clean(b.get('category')),clean(b.get('location')),clean(b.get('status','IN_USE')),b.get('last_audit')));audit(c,u[0],'ASSET_CREATED','asset',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path=='/api/v1/incidents':
    require(b,['type','description','severity']);sev=clean(b['severity']).upper();
    if sev not in SEVERITY:raise ValueError('invalid severity')
    cur=c.execute('INSERT INTO incidents(type,description,severity,status,reported_at) VALUES(?,?,?,?,?)',(clean(b['type']),clean(b['description']),sev,'REPORTED',now()));audit(c,u[0],'INCIDENT_REPORTED','incident',cur.lastrowid,None,b);c.commit();return self.sendj(201,{'id':cur.lastrowid})
   if path=='/api/v1/integrations':
    require(b,['kind']);kind=clean(b['kind']).upper();provider=clean(b.get('provider'));status=clean(b.get('status','NOT_CONFIGURED')).upper();
    if status not in ('NOT_CONFIGURED','ACTIVE','INACTIVE'):raise ValueError('invalid integration status')
    config=b.get('config',{});cur=c.execute('UPDATE integration_settings SET provider=?,status=?,config_json=?,updated_at=? WHERE kind=?',(provider,status,json.dumps(config),now(),kind));
    if cur.rowcount!=1:raise ValueError('unknown integration kind')
    audit(c,u[0],'INTEGRATION_CONFIGURED','integration',kind,None,{'kind':kind,'provider':provider,'status':status});c.commit();return self.sendj(200,{'kind':kind,'provider':provider,'status':status})
   return self.sendj(404,{'error':'not found'})
  except Exception as e:
   c.rollback();return self.sendj(400,{'error':str(e)})
  finally:c.close()
 def log_message(self,*a):pass

def worker():
 while True:
  try:materialize()
  except Exception as e:print('scheduler:',e)
  time.sleep(60)

PAGE='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ADMIN</title><style>body{margin:0;background:#f4f6f3;color:#17241c;font:14px system-ui}header{background:#214f3a;color:#fff;padding:18px;position:sticky;top:0}.wrap{max-width:1280px;margin:auto;padding:16px}.nav{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}.nav button,.btn{border:0;border-radius:7px;padding:9px 12px;background:#214f3a;color:white;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.card,.panel{background:#fff;border:1px solid #dce3dd;border-radius:10px;padding:14px;margin-bottom:14px}.n{font-size:25px;font-weight:700}.muted{color:#66736b}.danger{color:#a52e24}.ok{color:#267043}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:8px;border-bottom:1px solid #e5e9e6}input,select{padding:8px;border:1px solid #ccd4ce;border-radius:7px}.form{display:flex;gap:7px;flex-wrap:wrap}.pill{display:inline-block;padding:3px 7px;border-radius:99px;background:#edf1ed}</style></head><body><header><b>ADMIN</b><div>Farm &amp; Property Management · Operational System of Record</div></header><div class="wrap"><div class="nav"><button onclick="show('dashboard')">Dashboard</button><button onclick="show('tasks')">Tasks</button><button onclick="show('property')">Property &amp; Tenants</button><button onclick="show('finance')">Rent &amp; Payments</button><button onclick="show('operations')">Maintenance</button><button onclick="show('stock')">Stock &amp; Assets</button><button onclick="show('incidents')">Incidents</button><button onclick="show('admin')">Administration</button></div><div id="view"></div></div><script>
const $=id=>document.getElementById(id), esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));async function api(u,o){let r=await fetch(u,o);if(r.status===401){alert('Authentication required. Reload and sign in with your ADMIN credentials.');return null}let x=await r.json();if(!r.ok)throw Error(x.error||'Request failed');return x}function table(a){if(!a.length)return '<p class="muted">No records yet.</p>';let k=Object.keys(a[0]).slice(0,8);return '<div style="overflow:auto"><table><tr>'+k.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr>'+a.map(r=>'<tr>'+k.map(x=>'<td>'+esc(r[x])+'</td>').join('')+'</tr>').join('')+'</table></div>'}
async function show(v){try{if(v==='dashboard'){let s=await api('/api/v1/summary');$('view').innerHTML='<div class="grid">'+[['Due today',s.tasks.due_today,'ok'],['Overdue',s.tasks.overdue,'danger'],['Open tasks',s.tasks.open,''],['Properties',s.property.properties,''],['Units',s.property.units,''],['Vacant',s.property.vacant_units,''],['Arrears','M '+s.property.arrears,'danger'],['Maintenance',s.operations.maintenance_open,''],['Incidents',s.operations.incidents_open,'danger'],['Low stock',s.operations.low_stock,'']].map(x=>`<div class="card ${x[2]}"><div class="n">${x[1]}</div><div class="muted">${x[0]}</div></div>`).join('')+'</div><div class="panel"><h2>Quick actions</h2><div class="form"><button class="btn" onclick="newTask()">Create task</button><button class="btn" onclick="newTenant()">Add tenant</button><button class="btn" onclick="newMaintenance()">Log maintenance</button><button class="btn" onclick="newIncident()">Report incident</button></div></div>'}else if(v==='tasks'){let a=await api('/api/v1/tasks');$('view').innerHTML='<div class="panel"><h2>Task Register</h2><button class="btn" onclick="newTask()">+ Task</button>'+table(a)+'</div>'}else if(v==='property'){let [p,u,t]=await Promise.all([api('/api/v1/properties'),api('/api/v1/units'),api('/api/v1/tenants')]);$('view').innerHTML='<div class="panel"><h2>Properties</h2><button class="btn" onclick="newProperty()">+ Property</button>'+table(p)+'</div><div class="panel"><h2>Units</h2><button class="btn" onclick="newUnit()">+ Unit</button>'+table(u)+'</div><div class="panel"><h2>Tenants</h2><button class="btn" onclick="newTenant()">+ Tenant</button>'+table(t)+'</div>'}else if(v==='finance'){let [i,p]=await Promise.all([api('/api/v1/invoices'),api('/api/v1/payments')]);$('view').innerHTML='<div class="panel"><h2>Invoices</h2><button class="btn" onclick="newInvoice()">+ Invoice</button>'+table(i)+'</div><div class="panel"><h2>Payments (append-only)</h2>'+table(p)+'</div>'}else if(v==='operations'){let a=await api('/api/v1/maintenance');$('view').innerHTML='<div class="panel"><h2>Maintenance</h2><button class="btn" onclick="newMaintenance()">+ Request</button>'+table(a)+'</div>'}else if(v==='stock'){let [s,a]=await Promise.all([api('/api/v1/stock'),api('/api/v1/assets')]);$('view').innerHTML='<div class="panel"><h2>Stock</h2><button class="btn" onclick="newStock()">+ Item</button>'+table(s)+'</div><div class="panel"><h2>Assets</h2><button class="btn" onclick="newAsset()">+ Asset</button>'+table(a)+'</div>'}else if(v==='incidents'){let a=await api('/api/v1/incidents');$('view').innerHTML='<div class="panel"><h2>Incidents</h2><button class="btn" onclick="newIncident()">+ Incident</button>'+table(a)+'</div>'}else{let [i,a]=await Promise.all([api('/api/v1/integrations'),api('/api/v1/audit')]);$('view').innerHTML='<div class="panel"><h2>Integrations</h2><p class="muted">Providers and credentials are configured here, never hard-coded.</p>'+table(i)+'</div><div class="panel"><h2>Audit trail</h2>'+table(a)+'</div>'}}catch(e){$('view').innerHTML='<div class="panel danger">'+esc(e.message)+'</div>'}}
async function post(path,obj){await api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});show(current)}let current='dashboard';const old=show;show=async v=>{current=v;return old(v)};
async function newTask(){let title=prompt('Task title');if(!title)return;let due=prompt('Due date YYYY-MM-DD',new Date().toISOString().slice(0,10));if(due)await post('/api/v1/tasks',{title,due_date:due,area:'General',responsible:'Administrative Officer',priority:'MEDIUM'})}async function newProperty(){let name=prompt('Property name');if(name)await post('/api/v1/properties',{name})}async function newUnit(){let property_id=prompt('Property ID');let name=prompt('Unit name');if(property_id&&name)await post('/api/v1/units',{property_id,name,rent_amount:prompt('Monthly rent','0')})}async function newTenant(){let name=prompt('Tenant name');if(name)await post('/api/v1/tenants',{name,phone:prompt('Phone',''),email:prompt('Email',''),unit_id:prompt('Unit ID (optional)','')})}async function newInvoice(){let tenant_id=prompt('Tenant ID'),amount=prompt('Amount'),due_date=prompt('Due date YYYY-MM-DD',new Date().toISOString().slice(0,10));if(tenant_id&&amount&&due_date)await post('/api/v1/invoices',{tenant_id,amount,due_date})}async function newMaintenance(){let description=prompt('Maintenance description');if(description)await post('/api/v1/maintenance',{description,priority:prompt('Priority LOW/MEDIUM/HIGH/URGENT','MEDIUM')})}async function newStock(){let name=prompt('Stock item');if(name)await post('/api/v1/stock-items',{name,category:prompt('Category',''),reorder_level:prompt('Reorder level','0')})}async function newAsset(){let name=prompt('Asset name');if(name)await post('/api/v1/assets',{name,category:prompt('Category',''),location:prompt('Location','')})}async function newIncident(){let type=prompt('Incident type');let description=prompt('Description');if(type&&description)await post('/api/v1/incidents',{type,description,severity:prompt('Severity LOW/MEDIUM/HIGH/CRITICAL','MEDIUM')})}show('dashboard');</script></body></html>'''

if __name__=='__main__':
 init();materialize();threading.Thread(target=worker,daemon=True).start();print(f'ADMIN production server on http://127.0.0.1:{PORT}');ThreadingHTTPServer((HOST,PORT),H).serve_forever()
