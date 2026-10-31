"""
本機 smoke test：用 sqlite 模擬 Postgres，跑齊 API 路由。
（真正嘅 Postgres 驗證要等 deploy 之後打 live API 再做。）
"""
import os, re, sys, json, sqlite3, tempfile

sys.path.insert(0, "/workspace/bigtv/api")
os.environ.setdefault("BIGTV_PIN", "2468")

import _app  # noqa: E402

DB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = "sqlite-shim"   # 令 conn() 唔會 raise


class Cur:
    def __init__(self, cur):
        self.cur = cur
    def execute(self, sql, params=()):
        if "DROP COLUMN" in sql.upper():      # sqlite 唔支援，當 no-op
            return self
        sql = re.sub(r"SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT", sql, flags=re.I)
        sql = sql.replace("%s", "?")
        self.cur.execute(sql, params)
        return self
    def fetchone(self):
        r = self.cur.fetchone()
        return dict(r) if r is not None else None
    def fetchall(self):
        return [dict(r) for r in self.cur.fetchall()]
    def __enter__(self): return self
    def __exit__(self, *a): pass


class Conn:
    def __init__(self, path):
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA foreign_keys = ON")
    def cursor(self): return Cur(self.c.cursor())
    def __enter__(self): return self
    def __exit__(self, *a):
        self.c.commit()


def fake_conn(*a, **kw):
    return Conn(DB)


_app.conn = fake_conn
_app.DATABASE_URL = "sqlite-shim"

from fastapi.testclient import TestClient  # noqa: E402

cl = TestClient(_app.app, raise_server_exceptions=False)
fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))
    if not cond:
        fails.append(name)


# --- 基本 ---
r = cl.get("/api/ping"); check("ping", r.status_code == 200 and r.json()["ok"])

r = cl.get("/api/bank"); d = r.json()
check("seed bank", r.status_code == 200 and len(d["decks"]) == 6, r.text[:200])
items = sum(len(x["items"]) for x in d["decks"])
check("seed items = 62", items == 62, items)
check("no ban field", "ban" not in d["decks"][0]["items"][0])

# --- 登入 / 權限 ---
check("login wrong pin", cl.post("/api/login", json={"pin": "0000"}).status_code == 403)
tok = cl.post("/api/login", json={"pin": "2468"}).json()["token"]
H = {"X-Admin-Token": tok}
check("write without token", cl.post("/api/decks", json={"name": "x"}).status_code == 401)

# --- 類別 / 題目 ---
r = cl.post("/api/decks", json={"name": "測試類"}, headers=H); did = r.json()["id"]
check("deck add", r.status_code == 200 and did, r.text[:200])
r = cl.post(f"/api/decks/{did}/items", json={"items": ["題一", "題二", "題一", {"t": "題三"}]}, headers=H)
check("items dedupe = 3", r.json().get("added") == 3, r.text[:200])

d = cl.get("/api/bank").json()
deck = [x for x in d["decks"] if x["id"] == did][0]
check("deck items", [i["t"] for i in deck["items"]] == ["題一", "題二", "題三"], deck["items"])
iid = deck["items"][0]["id"]

check("item edit", cl.patch(f"/api/items/{iid}", json={"t": "題一改"}, headers=H).status_code == 200)
d = cl.get("/api/bank").json()
check("item edited", [x for x in d["decks"] if x["id"] == did][0]["items"][0]["t"] == "題一改")
check("item delete", cl.delete(f"/api/items/{iid}", headers=H).status_code == 200)
check("deck rename", cl.patch(f"/api/decks/{did}", json={"name": "改名類"}, headers=H).status_code == 200)
check("deck delete", cl.delete(f"/api/decks/{did}", headers=H).status_code == 200)
d = cl.get("/api/bank").json()
check("deck gone", not any(x["id"] == did for x in d["decks"]))

# --- 成績 / 排行榜 ---
r = cl.post("/api/sessions", json={"mode": "大電視", "rounds": 1, "questions": 3, "teams": [
    {"name": "阿明", "score": 4, "ok": 4, "skip": 0},
    {"name": "阿珍", "score": 2, "ok": 2, "skip": 1}]})
check("session add", r.status_code == 200 and r.json().get("id"))
cl.post("/api/sessions", json={"mode": "大電視", "rounds": 1, "questions": 2, "teams": [
    {"name": "阿明", "score": 1, "ok": 1, "skip": 0}]})
check("session empty teams rejected", cl.post("/api/sessions", json={"teams": []}).status_code == 400)

lb = cl.get("/api/leaderboard").json()
check("leaderboard totals", lb["players"][0] == {"name": "阿明", "total": 5, "best": 4, "games": 2,
                                                 "ok": 5, "skips": 0}, lb["players"][:1])
check("sessions_total = 2", lb["sessions_total"] == 2, lb["sessions_total"])
check("recent shape", lb["recent"][0]["winner"] in ("阿明", "阿珍"), lb["recent"][:1])

sid = cl.get("/api/sessions").json()["sessions"][0]["id"]
check("session delete", cl.delete(f"/api/sessions/{sid}", headers=H).status_code == 200)
check("sessions_total = 1 after delete", cl.get("/api/leaderboard").json()["sessions_total"] == 1)

# --- 整份取代 ---
r = cl.put("/api/bank", json={"name": "新庫", "decks": [{"name": "只有一類", "items": ["A", "B"]}]}, headers=H)
check("bank replace", r.status_code == 200, r.text[:200])
d = cl.get("/api/bank").json()
check("bank replaced", d["name"] == "新庫" and len(d["decks"]) == 1 and len(d["decks"][0]["items"]) == 2, d)

# --- reset ---
check("reset sessions", cl.post("/api/reset", json={"what": "sessions"}, headers=H).status_code == 200)
check("sessions cleared", cl.get("/api/leaderboard").json()["sessions_total"] == 0)

print("\n" + ("ALL PASS" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
