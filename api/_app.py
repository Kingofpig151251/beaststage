"""
百獸台 · Vercel API（FastAPI + Postgres）
------------------------------------------------------------------
題目就係一段純文字，冇分類、冇組合、冇 token。

  GET  /api/text   → {"text": "...", "title": "...", "subtitle": "...", "updated_at": "..."}
  PUT  /api/text   → 整份取代（無快照、無歷史）；title／subtitle 可選

遙控（第二部裝置做主持）
  POST /api/session            → {"id": "ABC123"}
  GET  /api/session/{id}?since=N → {"state":{...}, "seq":N, "cmds":[{"seq":1,"kind":"ok"}]}
  POST /api/session/{id}/cmd   → {"kind":"ok|skip|foul|ready|next|exit"} → {"seq":n}
  PUT  /api/session/{id}/state → 螢幕推送狀態給遙控顯示

環境變數
  DATABASE_URL   postgres://...（Neon / Vercel Marketplace 的 Postgres）
"""

import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
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


def conn():
    if not DATABASE_URL:
        raise RuntimeError("未設定 DATABASE_URL")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def ensure_schema():
    with conn() as c, c.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("""CREATE TABLE IF NOT EXISTS sess (
            id TEXT PRIMARY KEY,
            state JSONB NOT NULL DEFAULT '{}'::jsonb,
            touched TIMESTAMPTZ NOT NULL DEFAULT now())""")
        cur.execute("""CREATE TABLE IF NOT EXISTS cmd (
            seq BIGSERIAL PRIMARY KEY,
            sid TEXT NOT NULL,
            kind TEXT NOT NULL,
            ts TIMESTAMPTZ NOT NULL DEFAULT now())""")
        cur.execute("CREATE INDEX IF NOT EXISTS cmd_sid_seq ON cmd(sid, seq)")


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
@app.get("/api/text")
def text_get():
    schema()
    with conn() as c, c.cursor() as cur:
        text = read_text(cur)
        upd = get_meta(cur, "updated_at")
        title = get_meta(cur, "title") or ""
        subtitle = get_meta(cur, "subtitle") or ""
    return {"text": text, "title": title, "subtitle": subtitle, "updated_at": upd}


@app.put("/api/text")
async def text_put(request: Request):
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
    with conn() as c, c.cursor() as cur:
        put_meta(cur, "text", text)
        if title is not None:
            put_meta(cur, "title", title.strip()[:24])
        if subtitle is not None:
            put_meta(cur, "subtitle", subtitle.strip()[:36])
        put_meta(cur, "updated_at", now())
    return {"ok": True, "chars": len(text)}

# ------------------------------------------------------------------ 遙控
# 全部用單層路徑＋query／body 參數：Vercel 只穩定支援 /api/<one-segment>
KINDS = {"ok", "skip", "foul", "ready", "next", "exit"}
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # 無 I/O/0/1，避免讀錯


@app.post("/api/session")
def session_new():
    schema()
    sid = "".join(secrets.choice(ALPHABET) for _ in range(6))
    with conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM cmd WHERE ts < now() - interval '2 hours'")
        cur.execute("DELETE FROM sess WHERE touched < now() - interval '2 hours'")
        cur.execute("INSERT INTO sess(id) VALUES(%s)", (sid,))
    return {"id": sid}


@app.get("/api/session")
def session_get(id: str = "", since: int = 0):
    schema()
    if not id:
        return JSONResponse({"error": "缺少 id"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT state FROM sess WHERE id=%s", (id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "session 唔存在或已過期"}, status_code=404)
        cur.execute("SELECT seq, kind FROM cmd WHERE sid=%s AND seq>%s ORDER BY seq", (id, since))
        cmds = [{"seq": r["seq"], "kind": r["kind"]} for r in cur.fetchall()]
        cur.execute("UPDATE sess SET touched=now() WHERE id=%s", (id,))
    return {"state": row["state"], "cmds": cmds}


@app.post("/api/cmd")
async def session_cmd(request: Request):
    schema()
    body = await request.json()
    sid = body.get("id")
    kind = body.get("kind")
    if not sid or kind not in KINDS:
        return JSONResponse({"error": "id 或 kind 唔合法"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1 FROM sess WHERE id=%s", (sid,))
        if not cur.fetchone():
            return JSONResponse({"error": "session 唔存在或已過期"}, status_code=404)
        cur.execute("INSERT INTO cmd(sid, kind) VALUES(%s,%s) RETURNING seq", (sid, kind))
        seq = cur.fetchone()["seq"]
        cur.execute("UPDATE sess SET touched=now() WHERE id=%s", (sid,))
    return {"seq": seq}


@app.put("/api/state")
async def session_state(request: Request):
    schema()
    body = await request.json()
    sid = body.get("id")
    state = body.get("state")
    if not sid or not isinstance(state, dict):
        return JSONResponse({"error": "id 或 state 唔合法"}, status_code=400)
    with conn() as c, c.cursor() as cur:
        cur.execute("UPDATE sess SET state=%s::jsonb, touched=now() WHERE id=%s",
                    (json.dumps(state, ensure_ascii=False), sid))
        if cur.rowcount == 0:
            return JSONResponse({"error": "session 唔存在或已過期"}, status_code=404)
    return {"ok": True}
