"""
百獸台 · Vercel API（FastAPI + Postgres）
------------------------------------------------------------------
題目就係一段純文字，冇分類、冇組合、冇 token。

  GET  /api/text   → {"text": "...", "title": "...", "subtitle": "...", "updated_at": "..."}
  PUT  /api/text   → 整份取代（無快照、無歷史）；title／subtitle 可選

環境變數
  DATABASE_URL   postgres://...（Neon / Vercel Marketplace 的 Postgres）
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
EDIT_KEY = os.environ.get("EDIT_KEY") or ""      # 未設＝維持開放（本地開發用）
SEED = os.path.join(ROOT, "samples", "hk-icebreaker.json")

app = FastAPI(title="百獸台 API", docs_url=None, redoc_url=None, openapi_url=None)


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


_CONN = None


def conn():
    """重用同一個 warm 連線：每次新連線要 2 個 TLS round-trip，佔咗大部分延遲。"""
    global _CONN
    if not DATABASE_URL:
        raise RuntimeError("未設定 DATABASE_URL")
    if _CONN is not None:
        try:
            if not _CONN.closed:
                with _CONN.cursor() as cur:
                    cur.execute("SELECT 1")
                return _CONN
        except Exception:
            try: _CONN.close()
            except Exception: pass
        _CONN = None
    _CONN = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)
    return _CONN


@contextmanager
def db():
    """沿用 conn() 的寫法，但唔會關掉快取連線。"""
    c = conn()
    cur = c.cursor()
    try:
        yield c, cur
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        cur.close()


def ensure_schema():
    with db() as (c, cur):
        cur.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS reports ("
                    "id BIGSERIAL PRIMARY KEY, created_at TEXT NOT NULL, "
                    "kind TEXT, ua TEXT, vw INT, vh INT, body TEXT)")


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


def read_text(cur):
    text = get_meta(cur, "text")
    if text is None:
        text = seed_text()
        put_meta(cur, "text", text)
        put_meta(cur, "updated_at", now())
    return text


# ------------------------------------------------------------------ routes
def key_ok(request):
    """未設 EDIT_KEY 就唔檢查（本地開發／未配置環境變數時保持可用）。"""
    if not EDIT_KEY:
        return True
    return request.headers.get("x-edit-key", "") == EDIT_KEY


@app.get("/api/text")
def text_get(request: Request, check: int = 0):
    if check:                                   # /api/text?check=1：只驗密碼，唔讀 DB
        return {"ok": key_ok(request), "protected": bool(EDIT_KEY)}
    schema()
    with db() as (c, cur):
        text = read_text(cur)
        upd = get_meta(cur, "updated_at")
        title = get_meta(cur, "title") or ""
        subtitle = get_meta(cur, "subtitle") or ""
    return {"text": text, "title": title, "subtitle": subtitle, "updated_at": upd}


@app.put("/api/text")
async def text_put(request: Request):
    if not key_ok(request):
        return JSONResponse({"error": "未授權"}, status_code=401)
    schema()
    body = await request.json()
    text = body.get("text")
    if not isinstance(text, str):
        return JSONResponse({"error": "text 要係字串"}, status_code=400)
    text = text.replace("\r\n", "\n").replace("\r", "\n")[:200000]
    title, subtitle = body.get("title"), body.get("subtitle")
    if title is not None and not isinstance(title, str):
        return JSONResponse({"error": "title 要係字串"}, status_code=400)
    if subtitle is not None and not isinstance(subtitle, str):
        return JSONResponse({"error": "subtitle 要係字串"}, status_code=400)
    with db() as (c, cur):
        put_meta(cur, "text", text)
        if title is not None:
            put_meta(cur, "title", title.strip()[:24])
        if subtitle is not None:
            put_meta(cur, "subtitle", subtitle.strip()[:36])
        put_meta(cur, "updated_at", now())
    return {"ok": True, "chars": len(text)}


@app.post("/api/report")
async def report_post(request: Request):
    """玩家／主持回報問題（空白題等）。只寫 reports 表，唔會碰題庫。"""
    schema()
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse({"error": "body 要係物件"}, status_code=400)
    blob = json.dumps(body, ensure_ascii=False)[:20000]
    with db() as (c, cur):
        cur.execute("INSERT INTO reports (created_at, kind, ua, vw, vh, body) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (now(), str(body.get("kind") or "")[:40], str(body.get("ua") or "")[:300],
                     body.get("vw"), body.get("vh"), blob))
        cur.execute("DELETE FROM reports WHERE id NOT IN "
                    "(SELECT id FROM reports ORDER BY id DESC LIMIT 200)")   # 只留最近 200 筆
    return {"ok": True}


@app.get("/api/report")
def report_list(request: Request, limit: int = 20):
    if not key_ok(request):
        return JSONResponse({"error": "未授權"}, status_code=401)
    schema()
    with db() as (c, cur):
        cur.execute("SELECT id, created_at, kind, vw, vh, body FROM reports "
                    "ORDER BY id DESC LIMIT %s", (max(1, min(limit, 100)),))
        rows = [dict(r) for r in cur.fetchall()]
    return {"ok": True, "count": len(rows), "items": rows}
