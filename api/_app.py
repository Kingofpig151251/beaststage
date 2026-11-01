"""
大電視 · Vercel API（FastAPI + Postgres）
------------------------------------------------------------------
本地／NAS 用 `server.py`（Python 標準庫 + SQLite）；
雲端（Vercel）用呢個檔，因為 serverless 冇持久磁碟、實例之間亦唔共享記憶體。

環境變數（Vercel → Project → Settings → Environment Variables）
  DATABASE_URL   postgres://...（Neon / Vercel Marketplace 的 Postgres）

注意：題庫開放寫入（冇 token）；每次覆寫前留 3 份快照（meta: snap1–snap3）。
"""

import os
import re
import json
import time
import secrets
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
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
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)",
    ]
    with conn() as c, c.cursor() as cur:
        for sql in statements:
            cur.execute(sql)
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
        cur.execute("SELECT value FROM meta WHERE key='sets'")
        srow = cur.fetchone()
    import json as _json
    try:
        sets = _json.loads(srow["value"]) if srow and srow["value"] else []
    except Exception:
        sets = []
    return {"name": row["value"] if row else "題庫", "decks": decks, "sets": sets, "updated_at": upd}


def _snapshot(cur):
    """覆寫前將現有題庫存一份 JSON 快照，保留最近 3 份（meta key: snap1..snap3）。"""
    import json as _json
    cur.execute("SELECT key FROM meta WHERE key IN ('snap1','snap2','snap3')")
    have = {r["key"] for r in cur.fetchall()}
    cur.execute("SELECT id, name FROM decks ORDER BY sort, name")
    decks = []
    for d in cur.fetchall():
        cur.execute("SELECT text FROM items WHERE deck_id=%s ORDER BY sort, id", (d["id"],))
        decks.append({"id": d["id"], "name": d["name"], "items": [r["text"] for r in cur.fetchall()]})
    if not decks:
        return
    payload = _json.dumps({"decks": decks}, ensure_ascii=False)
    if "snap3" in have:
        cur.execute("DELETE FROM meta WHERE key='snap3'")
    cur.execute("UPDATE meta SET key='snap3' WHERE key='snap2'")
    cur.execute("UPDATE meta SET key='snap2' WHERE key='snap1'")
    cur.execute("INSERT INTO meta(key,value) VALUES('snap1',%s)", (payload,))


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


@app.put("/api/bank")
async def bank_replace(request: Request):
    # 開放寫入（題庫只存雲端、冇寫入碼）；每次覆寫前留低上一版做快照
    schema()
    body = await request.json()
    decks = body.get("decks")
    if not isinstance(decks, list):
        return JSONResponse({"error": "decks 要係 array"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        _snapshot(cur)
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
    sets = body.get("sets")
    if isinstance(sets, list):
        clean = []
        for s in sets[:30]:
            if not isinstance(s, dict):
                continue
            items = [str(t)[:60] for t in (s.get("items") or []) if str(t).strip()]
            clean.append({"id": str(s.get("id") or "")[:40] or "s"+str(len(clean)+1),
                          "name": str(s.get("name") or "組合")[:20], "items": items[:300]})
        import json as _json
        with conn() as c, c.cursor() as cur:
            cur.execute("INSERT INTO meta(key,value) VALUES('sets',%s) "
                        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                        (_json.dumps(clean, ensure_ascii=False),))
    return {"ok": True, "decks": len(decks)}
