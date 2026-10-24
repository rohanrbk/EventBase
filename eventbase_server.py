#!/usr/bin/env python3
"""Local EventBase working model: standard-library web server + SQLite API."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, sqlite3, uuid
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("EVENTBASE_DB", ROOT / "data" / "eventbase.sqlite3"))
HOST = os.environ.get("EVENTBASE_HOST", "127.0.0.1")
PORT = int(os.environ.get("EVENTBASE_PORT", "8000"))
SESSION_HOURS = 24


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def pw_hash(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return salt.hex(), digest.hex()


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('manager','participant')),
          salt TEXT NOT NULL, password_hash TEXT NOT NULL, org_id TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events(
          id TEXT PRIMARY KEY, org_id TEXT NOT NULL, name TEXT NOT NULL,
          type TEXT NOT NULL, date TEXT NOT NULL, format TEXT NOT NULL,
          location TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
          participants INTEGER NOT NULL DEFAULT 0, share_code TEXT UNIQUE NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_members(
          event_id TEXT NOT NULL REFERENCES events(id), user_id TEXT NOT NULL REFERENCES users(id),
          team TEXT NOT NULL DEFAULT 'Team Orbit', attendance TEXT NOT NULL DEFAULT 'Online',
          PRIMARY KEY(event_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS sessions(
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          event_id TEXT REFERENCES events(id), expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS checkins(
          event_id TEXT NOT NULL REFERENCES events(id), user_id TEXT NOT NULL REFERENCES users(id),
          checked_in_at TEXT NOT NULL, PRIMARY KEY(event_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS submissions(
          id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), user_id TEXT NOT NULL REFERENCES users(id),
          project_name TEXT NOT NULL, project_summary TEXT NOT NULL, demo_url TEXT NOT NULL DEFAULT '',
          repo_url TEXT NOT NULL DEFAULT '', files_json TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL,
          updated_at TEXT NOT NULL, UNIQUE(event_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS support_requests(
          id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), user_id TEXT NOT NULL REFERENCES users(id),
          category TEXT NOT NULL, message TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback(
          event_id TEXT NOT NULL REFERENCES events(id), user_id TEXT NOT NULL REFERENCES users(id),
          rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), message TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
          PRIMARY KEY(event_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS operations_state(
          event_id TEXT PRIMARY KEY REFERENCES events(id), payload TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL REFERENCES events(id),
          actor_id TEXT REFERENCES users(id), action TEXT NOT NULL, target TEXT NOT NULL DEFAULT '',
          details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        """)
        org = "eventbase-demo-org"
        users = [
            ("user-manager", "manager@eventbase.demo", "Alex Morgan", "manager", "eventbase-demo"),
            ("user-jordan", "jordan@eventbase.demo", "Jordan Patel", "participant", "participant-demo"),
        ]
        for uid, email, name, role, password in users:
            if not db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                salt, digest = pw_hash(password)
                db.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?)", (uid,email,name,role,salt,digest,org))
        events = [
            ("EV-01", "Hack the Future 2025", "Hackathon", "2025-10-18", "Hybrid", "The Foundry · Bengaluru", "Live", 248, "FUTURE25"),
            ("EV-02", "AI for Earth Summit", "Conference", "2026-12-04", "In-person", "Mumbai · The NCPA", "Upcoming", 0, "EARTH26"),
        ]
        for eid,name,etype,date,fmt,loc,status,count,code in events:
            db.execute("INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)", (eid,org,name,etype,date,fmt,loc,status,count,code,datetime.now(timezone.utc).isoformat()))
        db.execute("INSERT OR IGNORE INTO event_members(event_id,user_id,team,attendance) VALUES('EV-01','user-jordan','Team Orbit','Online')")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def send_json(self, status, payload, headers=None):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)

    def body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 1_000_000: raise ValueError("Request body too large")
        raw = self.rfile.read(size) if size else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict): raise ValueError("JSON object required")
        return value

    def actor(self):
        cookie = self.headers.get("Cookie", "")
        token = next((part.strip().split("=",1)[1] for part in cookie.split(";") if part.strip().startswith("eb_session=")), None)
        if not token: return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with connect() as db:
            row = db.execute("SELECT u.*,s.event_id,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?", (digest,)).fetchone()
            if not row: return None
            if row["expires_at"] < now():
                db.execute("DELETE FROM sessions WHERE token_hash=?", (digest,)); return None
            return dict(row)

    def require(self, role=None):
        user = self.actor()
        if not user: self.send_json(401,{"error":"Sign in required"}); return None
        if role and user["role"] != role:
            self.send_json(403,{"error":"This role cannot access that action"}); return None
        return user

    def do_GET(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            if path == "/": self.path = "/index.html"
            return super().do_GET()
        if path == "/api/health": return self.send_json(200,{"ok":True,"product":"EventBase"})
        if path == "/api/me":
            user=self.actor()
            if not user:return self.send_json(200,{"authenticated":False})
            return self.send_json(200,{"authenticated":True,"user":{"name":user["name"],"email":user["email"],"role":user["role"]},"event_id":user["event_id"]})
        if path == "/api/events":
            user=self.require()
            if not user:return
            with connect() as db:
                if user["role"]=="manager": rows=db.execute("SELECT * FROM events WHERE org_id=? ORDER BY date DESC",(user["org_id"],)).fetchall()
                else: rows=db.execute("SELECT e.* FROM events e JOIN event_members m ON m.event_id=e.id WHERE m.user_id=? ORDER BY e.date DESC",(user["id"],)).fetchall()
            return self.send_json(200,{"events":[self.event_dict(x) for x in rows]})
        if path == "/api/participant/summary":
            user=self.require("participant")
            if not user:return
            eid=user["event_id"]
            if not eid:return self.send_json(404,{"error":"No event linked to this participant"})
            with connect() as db:
                member=db.execute("SELECT * FROM event_members WHERE event_id=? AND user_id=?",(eid,user["id"])).fetchone()
                check=db.execute("SELECT checked_in_at FROM checkins WHERE event_id=? AND user_id=?",(eid,user["id"])).fetchone()
                sub=db.execute("SELECT * FROM submissions WHERE event_id=? AND user_id=?",(eid,user["id"])).fetchone()
                req=db.execute("SELECT * FROM support_requests WHERE event_id=? AND user_id=? ORDER BY created_at DESC",(eid,user["id"])).fetchall()
                fb=db.execute("SELECT * FROM feedback WHERE event_id=? AND user_id=?",(eid,user["id"])).fetchone()
            return self.send_json(200,{"event_id":eid,"team":member["team"] if member else "Team Orbit","attendance":member["attendance"] if member else "Online","checked_in":bool(check),"submission":dict(sub) if sub else None,"support_requests":[dict(r) for r in req],"feedback":dict(fb) if fb else None})
        if path == "/api/ops-state":
            user=self.require("manager")
            if not user:return
            eid=urlparse(self.path).query.split("event_id=",1)[-1] if "event_id=" in self.path else "EV-01"
            with connect() as db:
                if not db.execute("SELECT 1 FROM events WHERE id=? AND org_id=?",(eid,user["org_id"])).fetchone():return self.send_json(404,{"error":"Event not found"})
                row=db.execute("SELECT payload FROM operations_state WHERE event_id=?",(eid,)).fetchone()
            return self.send_json(200,{"state":json.loads(row["payload"]) if row else None})
        if path == "/api/support":
            user=self.require()
            if not user:return
            with connect() as db:
                if user["role"]=="manager":rows=db.execute("SELECT r.*,u.name AS participant FROM support_requests r JOIN users u ON u.id=r.user_id WHERE r.event_id IN (SELECT id FROM events WHERE org_id=?) ORDER BY r.created_at DESC",(user["org_id"],)).fetchall()
                else:rows=db.execute("SELECT * FROM support_requests WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
            return self.send_json(200,{"requests":[dict(r) for r in rows]})
        return self.send_json(404,{"error":"API route not found"})

    @staticmethod
    def event_dict(row):
        return {"id":row["id"],"name":row["name"],"type":row["type"],"date":row["date"],"format":row["format"],"location":row["location"],"status":row["status"],"participants":row["participants"],"share_code":row["share_code"]}

    def do_POST(self):
        path=urlparse(self.path).path
        try: data=self.body()
        except Exception as exc:return self.send_json(400,{"error":str(exc)})
        if path=="/api/login":
            email=str(data.get("email"," ")).strip().lower();password=str(data.get("password",""));role=data.get("role")
            if "@" not in email or role not in ("manager","participant"):return self.send_json(400,{"error":"Enter a valid email and choose a role"})
            with connect() as db:
                event_id=None
                if role=="manager":
                    user=db.execute("SELECT * FROM users WHERE email=? AND role='manager'",(email,)).fetchone()
                    if not user:return self.send_json(401,{"error":"Email or password is incorrect"})
                    salt=bytes.fromhex(user["salt"]);check=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,180_000).hex()
                    if not hmac.compare_digest(check,user["password_hash"]):return self.send_json(401,{"error":"Email or password is incorrect"})
                else:
                    code=str(data.get("event_code"," ")).strip().upper()
                    event=db.execute("SELECT id,org_id FROM events WHERE share_code=?",(code,)).fetchone()
                    if not event:return self.send_json(401,{"error":"That event access code was not found"})
                    user=db.execute("SELECT * FROM users WHERE email=? AND role='participant'",(email,)).fetchone()
                    if not user:
                        name=str(data.get("name",email.split("@",1)[0].replace("."," ").replace("_"," ").title()))[:100]
                        uid="user-"+uuid.uuid4().hex[:12];salt_hex,digest=pw_hash(secrets.token_urlsafe(24))
                        db.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?)",(uid,email,name,"participant",salt_hex,digest,event["org_id"]))
                        user=db.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
                    member=db.execute("SELECT 1 FROM event_members WHERE event_id=? AND user_id=?",(event["id"],user["id"])).fetchone()
                    if not member:
                        db.execute("INSERT INTO event_members(event_id,user_id,team,attendance) VALUES(?,?,?,?)",(event["id"],user["id"],"New team","Online"))
                        db.execute("UPDATE events SET participants=participants+1 WHERE id=?",(event["id"],))
                    event_id=event["id"]
                token=secrets.token_urlsafe(32);token_hash=hashlib.sha256(token.encode()).hexdigest();expires=(datetime.now(timezone.utc)+timedelta(hours=SESSION_HOURS)).isoformat()
                db.execute("INSERT INTO sessions VALUES(?,?,?,?)",(token_hash,user["id"],event_id,expires))
                self.audit(db,user["id"],event_id,"login",email,"Role-specific sign-in")
            cookie=f"eb_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={SESSION_HOURS*3600}"
            return self.send_json(200,{"authenticated":True,"user":{"name":user["name"],"email":user["email"],"role":role},"event_id":event_id},{"Set-Cookie":cookie})
        if path=="/api/logout":
            actor=self.actor()
            if actor:
                cookie=self.headers.get("Cookie","");token=next((p.strip().split("=",1)[1] for p in cookie.split(";") if p.strip().startswith("eb_session=")),"")
                with connect() as db:db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))
            return self.send_json(200,{"ok":True},{"Set-Cookie":"eb_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"})
        if path=="/api/events":
            user=self.require("manager")
            if not user:return
            name=str(data.get("name","")).strip();date=str(data.get("date","")).strip();etype=str(data.get("type","Other")).strip();fmt=str(data.get("format","Hybrid")).strip();loc=str(data.get("location","")).strip()
            if not name or not date:return self.send_json(400,{"error":"Event name and date are required"})
            if len(name)>120 or len(loc)>160:return self.send_json(400,{"error":"Event details are too long"})
            eid="EV-"+uuid.uuid4().hex[:8].upper();code=secrets.token_hex(3).upper()
            with connect() as db:
                db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",(eid,user["org_id"],name,etype,date,fmt,loc,"Draft",0,code,now()))
                self.audit(db,user["id"],eid,"event.created",name,f"Draft event created; share code {code}")
                row=db.execute("SELECT * FROM events WHERE id=?",(eid,)).fetchone()
            return self.send_json(201,{"event":self.event_dict(row)})
        if path=="/api/checkin":
            user=self.require("participant")
            if not user:return
            eid=user["event_id"]
            if not eid:return self.send_json(400,{"error":"No event is linked to this participant"})
            with connect() as db:
                db.execute("INSERT INTO checkins VALUES(?,?,?) ON CONFLICT(event_id,user_id) DO UPDATE SET checked_in_at=excluded.checked_in_at",(eid,user["id"],now()))
                self.audit(db,user["id"],eid,"participant.checkin",user["email"],"Checked in")
            return self.send_json(200,{"checked_in":True})
        if path=="/api/submission":
            user=self.require("participant")
            if not user:return
            eid=user["event_id"];name=str(data.get("project_name","")).strip();summary=str(data.get("project_summary","")).strip()
            if not eid:return self.send_json(400,{"error":"No event is linked to this participant"})
            if not name or not summary:return self.send_json(400,{"error":"Project name and summary are required"})
            files=json.dumps([str(x)[:180] for x in data.get("files",[])[:10]])
            status="Submitted" if data.get("submit") else "Draft";sid="SUB-"+uuid.uuid4().hex[:8].upper();stamp=now()
            with connect() as db:
                db.execute("INSERT INTO submissions VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(event_id,user_id) DO UPDATE SET project_name=excluded.project_name,project_summary=excluded.project_summary,demo_url=excluded.demo_url,repo_url=excluded.repo_url,files_json=excluded.files_json,status=excluded.status,updated_at=excluded.updated_at",(sid,eid,user["id"],name,summary,str(data.get("demo_url",""))[:500],str(data.get("repo_url",""))[:500],files,status,stamp))
                self.audit(db,user["id"],eid,"submission.saved",name,status)
            return self.send_json(200,{"status":status,"updated_at":stamp,"files_recorded":json.loads(files),"uploaded":False})
        if path=="/api/support":
            user=self.require("participant")
            if not user:return
            eid=user["event_id"];msg=str(data.get("message","")).strip();category=str(data.get("category","General help"))[:80];kind=str(data.get("kind","mentor"))
            if not eid or not msg:return self.send_json(400,{"error":"An event and support message are required"})
            rid="SUP-"+uuid.uuid4().hex[:6].upper()
            with connect() as db:
                db.execute("INSERT INTO support_requests VALUES(?,?,?,?,?,?,?,?)",(rid,eid,user["id"],category,msg[:2000],kind,"Received",now()))
                self.audit(db,user["id"],eid,"support.request",rid,category)
            return self.send_json(201,{"id":rid,"status":"Received","stored":True,"staff_notified":False})
        if path=="/api/feedback":
            user=self.require("participant")
            if not user:return
            eid=user["event_id"];rating=int(data.get("rating",0));msg=str(data.get("message",""))[:2000]
            if not eid or rating<1 or rating>5:return self.send_json(400,{"error":"Select a rating from 1 to 5"})
            with connect() as db:
                db.execute("INSERT INTO feedback VALUES(?,?,?,?,?) ON CONFLICT(event_id,user_id) DO UPDATE SET rating=excluded.rating,message=excluded.message,created_at=excluded.created_at",(eid,user["id"],rating,msg,now()))
                self.audit(db,user["id"],eid,"feedback.saved",str(rating),"Participant feedback stored")
            return self.send_json(200,{"saved":True})
        if path=="/api/ops-state":
            user=self.require("manager")
            if not user:return
            eid=str(data.get("event_id","EV-01"));payload=data.get("state")
            if not isinstance(payload,dict):return self.send_json(400,{"error":"State object is required"})
            with connect() as db:
                if not db.execute("SELECT 1 FROM events WHERE id=? AND org_id=?",(eid,user["org_id"])).fetchone():return self.send_json(404,{"error":"Event not found"})
                db.execute("INSERT INTO operations_state VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",(eid,json.dumps(payload,ensure_ascii=False),now()))
            return self.send_json(200,{"saved":True})
        return self.send_json(404,{"error":"API route not found"})

    @staticmethod
    def audit(db, actor, event, action, target="", details=""):
        if event: db.execute("INSERT INTO audit_log(event_id,actor_id,action,target,details,created_at) VALUES(?,?,?,?,?,?)",(event,actor,action,target,details,now()))

    def end_headers(self):
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","same-origin")
        super().end_headers()


def main():
    init_db()
    print(f"EventBase running at http://{HOST}:{PORT}")
    print("Demo manager: manager@eventbase.demo / eventbase-demo · participant: jordan@eventbase.demo with event code FUTURE25")
    print(f"SQLite data: {DB_PATH}")
    try: ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
    except KeyboardInterrupt: print("\nEventBase server stopped.")

if __name__=="__main__": main()




