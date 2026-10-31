"""
大電視 · Vercel API（FastAPI + Postgres）
------------------------------------------------------------------
本地／NAS 用 `server.py`（Python 標準庫 + SQLite）；
雲端（Vercel）用呢個檔，因為 serverless 冇持久磁碟、實例之間亦唔共享記憶體。

環境變數（Vercel → Project → Settings → Environment Variables）
  DATABASE_URL   postgres://...（Neon / Vercel Marketplace 的 Postgres）
  BIGTV_PIN      後台密碼，預設 2468（正式一定要改）
  BIGTV_SECRET   簽 token 用；唔設就由 PIN 派生（改 PIN 會令舊 token 失效）

注意：token 用 HMAC 簽名而唔存記憶體 —— serverless 每次可能係另一個實例。
"""

import os
import re
import json
import time
import hmac
import hashlib
import secrets
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
ADMIN_PIN = os.environ.get("BIGTV_PIN", "2468")
SECRET = (os.environ.get("BIGTV_SECRET") or hashlib.sha256(ADMIN_PIN.encode()).hexdigest()).encode()
TOKEN_TTL = 12 * 3600
SEED = os.path.join(ROOT, "samples", "hk-icebreaker.json")

app = FastAPI(title="大電視 API", docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(Exception)
async def any_error(request: Request, exc: Exception):
    """serverless 出錯時要回 JSON，唔好回空白 500。"""
    msg = str(exc)
    if "DATABASE_URL" in msg:
        msg = "未設定 DATABASE_URL（去 Vercel 專案加 Postgres）"
    return JSONResponse({"error": msg}, status_code=503)


# ------------------------------------------------------------------ util
def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def conn():
    if not DATABASE_URL:
        raise RuntimeError("未設定 DATABASE_URL")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def ensure_schema():
    """每次冷啟跑一次；CREATE IF NOT EXISTS 係 idempotent。"""
    # 一句一句執行：psycopg3 唔保證可以一次過送多條 statement
    statements = [
        """CREATE TABLE IF NOT EXISTS decks (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, sort INTEGER DEFAULT 0, updated_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            deck_id TEXT NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
            text TEXT NOT NULL, sort INTEGER DEFAULT 0)""",
        "CREATE INDEX IF NOT EXISTS idx_items_deck ON items(deck_id)",
        """CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY, finished_at TEXT NOT NULL, mode TEXT,
            rounds INTEGER, questions INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS results (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            player TEXT NOT NULL, score INTEGER DEFAULT 0,
            ok INTEGER DEFAULT 0, skip INTEGER DEFAULT 0)""",
        "CREATE INDEX IF NOT EXISTS idx_results_session ON results(session_id)",
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)",
    ]
    with conn() as c, c.cursor() as cur:
        for sql in statements:
            cur.execute(sql)
        # 舊 DB 仲有 miss 欄（已無用途）
        cur.execute("ALTER TABLE results DROP COLUMN IF EXISTS miss")
        cur.execute("SELECT COUNT(*) AS c FROM decks")
        if cur.fetchone()["c"] == 0 and os.path.exists(SEED):
            with open(SEED, encoding="utf-8") as f:
                seed = json.load(f)
            for i, d in enumerate(seed.get("decks", [])):
                cur.execute("INSERT INTO decks(id,name,sort,updated_at) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                            (d["id"], d["name"], i, now()))
                for j, it in enumerate(d.get("items", [])):
                    t = (it if isinstance(it, str) else it.get("t", "")).strip()
                    if t:
                        cur.execute("INSERT INTO items(deck_id,text,sort) VALUES(%s,%s,%s)", (d["id"], t, j))
            cur.execute("INSERT INTO meta(key,value) VALUES('name',%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                        (seed.get("name", "香港破冰題庫"),))


_SCHEMA_READY = {"ok": False}


def schema():
    if not _SCHEMA_READY["ok"]:
        ensure_schema()
        _SCHEMA_READY["ok"] = True


def read_bank(c):
    with c.cursor() as cur:
        cur.execute("SELECT value FROM meta WHERE key='name'")
        row = cur.fetchone()
        cur.execute("SELECT id, name FROM decks ORDER BY sort, name")
        decks = []
        for d in cur.fetchall():
            cur.execute("SELECT id, text FROM items WHERE deck_id=%s ORDER BY sort, id", (d["id"],))
            decks.append({"id": d["id"], "name": d["name"],
                          "items": [{"id": r["id"], "t": r["text"]} for r in cur.fetchall()]})
        cur.execute("SELECT MAX(updated_at) AS u FROM decks")
        upd = cur.fetchone()["u"]
    return {"name": row["value"] if row else "題庫", "decks": decks, "updated_at": upd}


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "deck"


def unique_deck_id(cur, base):
    cand, i = base, 2
    while True:
        cur.execute("SELECT 1 FROM decks WHERE id=%s", (cand,))
        if not cur.fetchone():
            return cand
        cand = f"{base}-{i}"
        i += 1


# ------------------------------------------------------------------ auth
def make_token():
    exp = int(time.time()) + TOKEN_TTL
    sig = hmac.new(SECRET, str(exp).encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def token_ok(tok: str) -> bool:
    if not ADMIN_PIN:
        return True
    try:
        exp_s, sig = tok.split(".")
        exp = int(exp_s)
    except Exception:
        return False
    if exp < time.time():
        return False
    good = hmac.new(SECRET, exp_s.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good)


def need_token(request: Request):
    if token_ok(request.headers.get("x-admin-token", "")):
        return None
    return JSONResponse({"error": "需要後台登入"}, status_code=401)


# ------------------------------------------------------------------ middleware
@app.middleware("http")
async def normalize_path(request: Request, call_next):
    """Vercel 可能將 /api/bank 直接餵入函數（[path] catch-all），亦可能係 /bank。"""
    path = request.scope.get("path", "/")
    if not path.startswith("/api"):
        request.scope["path"] = "/api" + (path if path.startswith("/") else "/" + path)
    return await call_next(request)


# ------------------------------------------------------------------ routes
@app.get("/api/ping")
def ping():
    return {"ok": True, "time": now(), "version": 2, "db": bool(DATABASE_URL)}


@app.get("/api/bank")
def bank_get():
    schema()
    with conn() as c:
        return read_bank(c)


@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    pin = str(body.get("pin", ""))
    if ADMIN_PIN and hmac.compare_digest(pin, ADMIN_PIN):
        return {"token": make_token(), "expires_in": TOKEN_TTL}
    return JSONResponse({"error": "密碼唔對"}, status_code=403)


@app.get("/api/leaderboard")
def leaderboard(limit: int = 10):
    schema()
    limit = max(1, min(100, limit))
    with conn() as c, c.cursor() as cur:
        cur.execute("""
            SELECT r.player AS name, SUM(r.score) AS total, MAX(r.score) AS best,
                   COUNT(*) AS games, SUM(r.ok) AS ok, SUM(r.skip) AS skips
            FROM results r GROUP BY r.player
            ORDER BY total DESC, best DESC, games DESC LIMIT %s""", (limit,))
        players = cur.fetchall()
        cur.execute("""
            SELECT s.id, s.finished_at, s.mode, s.rounds, s.questions,
                   (SELECT player FROM results WHERE session_id=s.id ORDER BY score DESC, ok DESC LIMIT 1) AS winner,
                   (SELECT score  FROM results WHERE session_id=s.id ORDER BY score DESC, ok DESC LIMIT 1) AS winner_score,
                   (SELECT COUNT(*) FROM results WHERE session_id=s.id) AS players
            FROM sessions s ORDER BY s.id DESC LIMIT %s""", (limit,))
        recent = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c FROM sessions")
        total = cur.fetchone()["c"]
    return {"players": players, "recent": recent, "sessions_total": total}


@app.post("/api/sessions")
async def session_add(request: Request):
    schema()
    body = await request.json()
    teams = body.get("teams") or []
    if not isinstance(teams, list) or not teams:
        return JSONResponse({"error": "teams 唔可以空"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO sessions(finished_at,mode,rounds,questions) VALUES(%s,%s,%s,%s) RETURNING id",
                    (now(), str(body.get("mode", ""))[:40], int(body.get("rounds") or 0),
                     int(body.get("questions") or 0)))
        sid = cur.fetchone()["id"]
        for t in teams[:16]:
            cur.execute("INSERT INTO results(session_id,player,score,ok,skip) VALUES(%s,%s,%s,%s,%s)",
                        (sid, str(t.get("name", "?"))[:40] or "?", int(t.get("score") or 0),
                         int(t.get("ok") or 0), int(t.get("skip") or 0)))
    return {"id": sid, "ok": True}


@app.get("/api/sessions")
def sessions_list(limit: int = 20):
    schema()
    limit = max(1, min(200, limit))
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT id, finished_at, mode, rounds, questions FROM sessions ORDER BY id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        for r in rows:
            cur.execute("SELECT player,score,ok,skip FROM results WHERE session_id=%s ORDER BY score DESC", (r["id"],))
            r["results"] = cur.fetchall()
    return {"sessions": rows}


@app.delete("/api/sessions/{sid}")
def session_del(sid: int, request: Request):
    if (r := need_token(request)):
        return r
    schema()
    with conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE id=%s", (sid,))
    return {"ok": True}


@app.post("/api/decks")
async def deck_add(request: Request):
    if (r := need_token(request)):
        return r
    schema()
    body = await request.json()
    name = str(body.get("name", "")).strip()
    if not name:
        return JSONResponse({"error": "類別名唔可以空"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        did = unique_deck_id(cur, slug(body.get("id") or name))
        cur.execute("SELECT COALESCE(MAX(sort),0)+1 AS s FROM decks")
        s = cur.fetchone()["s"]
        cur.execute("INSERT INTO decks(id,name,sort,updated_at) VALUES(%s,%s,%s,%s)", (did, name[:40], s, now()))
    return {"id": did, "name": name}


@app.patch("/api/decks/{did}")
async def deck_rename(did: str, request: Request):
    if (r := need_token(request)):
        return r
    schema()
    body = await request.json()
    name = str(body.get("name", "")).strip()
    if not name:
        return JSONResponse({"error": "類別名唔可以空"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        cur.execute("UPDATE decks SET name=%s, updated_at=%s WHERE id=%s", (name[:40], now(), did))
    return {"ok": True}


@app.delete("/api/decks/{did}")
def deck_del(did: str, request: Request):
    if (r := need_token(request)):
        return r
    schema()
    with conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM decks WHERE id=%s", (did,))
    return {"ok": True}


@app.post("/api/decks/{did}/items")
async def items_add(did: str, request: Request):
    if (r := need_token(request)):
        return r
    schema()
    body = await request.json()
    items = body.get("items") or []
    if not isinstance(items, list):
        return JSONResponse({"error": "items 要係 array"}, status_code=400)
    added = 0
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1 FROM decks WHERE id=%s", (did,))
        if not cur.fetchone():
            return JSONResponse({"error": "類別唔存在"}, status_code=400)
        cur.execute("SELECT COALESCE(MAX(sort),0)+1 AS s FROM items WHERE deck_id=%s", (did,))
        s = cur.fetchone()["s"]
        cur.execute("SELECT text FROM items WHERE deck_id=%s", (did,))
        existing = {r["text"] for r in cur.fetchall()}
        for it in items[:500]:
            t = (it if isinstance(it, str) else it.get("t", "")).strip()
            if not t or t in existing:
                continue
            cur.execute("INSERT INTO items(deck_id,text,sort) VALUES(%s,%s,%s)", (did, t[:200], s))
            existing.add(t)
            s += 1
            added += 1
        cur.execute("UPDATE decks SET updated_at=%s WHERE id=%s", (now(), did))
    return {"added": added}


@app.patch("/api/items/{iid}")
async def item_edit(iid: int, request: Request):
    if (r := need_token(request)):
        return r
    schema()
    body = await request.json()
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM items WHERE id=%s", (iid,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "題目唔存在"}, status_code=400)
        t = str(body.get("t", row["text"])).strip()[:200] or row["text"]
        cur.execute("UPDATE items SET text=%s WHERE id=%s", (t, iid))
        cur.execute("UPDATE decks SET updated_at=%s WHERE id=%s", (now(), row["deck_id"]))
    return {"ok": True}


@app.delete("/api/items/{iid}")
def item_del(iid: int, request: Request):
    if (r := need_token(request)):
        return r
    schema()
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT deck_id FROM items WHERE id=%s", (iid,))
        row = cur.fetchone()
        cur.execute("DELETE FROM items WHERE id=%s", (iid,))
        if row:
            cur.execute("UPDATE decks SET updated_at=%s WHERE id=%s", (now(), row["deck_id"]))
    return {"ok": True}


@app.put("/api/bank")
async def bank_replace(request: Request):
    if (r := need_token(request)):
        return r
    schema()
    body = await request.json()
    decks = body.get("decks")
    if not isinstance(decks, list):
        return JSONResponse({"error": "decks 要係 array"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM items")
        cur.execute("DELETE FROM decks")
        if body.get("name"):
            cur.execute("INSERT INTO meta(key,value) VALUES('name',%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                        (str(body["name"])[:60],))
        for i, d in enumerate(decks[:60]):
            did = unique_deck_id(cur, slug(d.get("id") or d.get("name")))
            cur.execute("INSERT INTO decks(id,name,sort,updated_at) VALUES(%s,%s,%s,%s)",
                        (did, str(d.get("name", did))[:40], i, now()))
            for j, it in enumerate(d.get("items", [])[:800]):
                t = (it if isinstance(it, str) else it.get("t", "")).strip()
                if not t:
                    continue
                cur.execute("INSERT INTO items(deck_id,text,sort) VALUES(%s,%s,%s)", (did, t[:200], j))
    return {"ok": True, "decks": len(decks)}


@app.post("/api/reset")
async def reset(request: Request):
    if (r := need_token(request)):
        return r
    schema()
    body = await request.json()
    what = body.get("what", "")
    with conn() as c, c.cursor() as cur:
        if what == "sessions":
            cur.execute("DELETE FROM results")
            cur.execute("DELETE FROM sessions")
        elif what == "bank":
            cur.execute("DELETE FROM items")
            cur.execute("DELETE FROM decks")
    return {"ok": True}
