"""
大電視 · Vercel API（FastAPI + Postgres）
------------------------------------------------------------------
題目就係一段純文字，冇分類、冇組合、冇 token。

  GET  /api/ping
  GET  /api/text   → {"text": "...", "updated_at": "..."}
  PUT  /api/text   → 整份取代；每次覆寫前留 3 份快照（meta: snap1–snap3）

環境變數
  DATABASE_URL   postgres://...（Neon / Vercel Marketplace 的 Postgres）
"""

import json
import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
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
    with conn() as c, c.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")


_READY = {"ok": False}


def schema():
    if not _READY["ok"]:
        ensure_schema()
        _READY["ok"] = True


def get_meta(cur, key):
    cur.execute("SELECT value FROM meta WHERE key=%s", (key,))
    row = cur.fetchone()
    return row["value"] if row else None


def put_meta(cur, key, value):
    cur.execute("INSERT INTO meta(key,value) VALUES(%s,%s) "
                "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value))


def seed_text():
    """第一次用：由 samples 抽題目，一行一題（類別名唔要）。"""
    try:
        with open(SEED, encoding="utf-8") as f:
            seed = json.load(f)
    except Exception:
        return ""
    out = []
    for d in seed.get("decks", []):
        for it in d.get("items", []):
            t = (it if isinstance(it, str) else it.get("t", "")).strip()
            if t:
                out.append(t)
    return "\n".join(out)


def legacy_text(cur):
    """舊版存 decks/items；有就轉成一段文字（一次性遷移）。"""
    try:
        cur.execute("SELECT id FROM decks ORDER BY sort, name")
        decks = cur.fetchall()
    except Exception:
        return None
    if not decks:
        return None
    out = []
    for d in decks:
        cur.execute("SELECT text FROM items WHERE deck_id=%s ORDER BY sort, id", (d["id"],))
        for r in cur.fetchall():
            if r["text"].strip():
                out.append(r["text"].strip())
    return "\n".join(out) if out else None


def read_text(cur):
    text = get_meta(cur, "text")
    if text is None:
        text = legacy_text(cur)
        if text is None:
            text = seed_text()
        put_meta(cur, "text", text)
        put_meta(cur, "updated_at", now())
    return text


def snapshot(cur, text):
    """覆寫前留 3 份：snap3 ← snap2 ← snap1 ← 舊內容。"""
    if not text:
        return
    s1 = get_meta(cur, "snap1")
    s2 = get_meta(cur, "snap2")
    if s2:
        put_meta(cur, "snap3", s2)
    if s1:
        put_meta(cur, "snap2", s1)
    put_meta(cur, "snap1", text)


# ------------------------------------------------------------------ routes
@app.get("/api/ping")
def ping():
    schema()
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1")
    return {"ok": True, "time": now(), "version": 3, "db": True}


@app.get("/api/text")
def text_get():
    schema()
    with conn() as c, c.cursor() as cur:
        text = read_text(cur)
        upd = get_meta(cur, "updated_at")
    return {"text": text, "updated_at": upd}


@app.put("/api/text")
async def text_put(request: Request):
    schema()
    body = await request.json()
    text = body.get("text")
    if not isinstance(text, str):
        return JSONResponse({"error": "text 要係字串"}, status_code=400)
    text = text.replace("\r\n", "\n").replace("\r", "\n")[:200000]
    with conn() as c, c.cursor() as cur:
        snapshot(cur, get_meta(cur, "text"))
        put_meta(cur, "text", text)
        put_meta(cur, "updated_at", now())
    return {"ok": True, "chars": len(text)}
