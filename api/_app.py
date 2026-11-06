"""
百獸台 · Vercel API（FastAPI + Postgres）
------------------------------------------------------------------
題目就係一段純文字，冇分類、冇組合、冇 token。

  GET  /api/text   → {"text": "...", "title": "...", "subtitle": "...", "updated_at": "..."}
  PUT  /api/text   → 整份取代（無快照、無歷史）；title／subtitle 可選

環境變數
  DATABASE_URL   postgres://...（Neon / Vercel Marketplace 的 Postgres）
"""

import hashlib
import json
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
EDIT_KEY = os.environ.get("EDIT_KEY") or ""      # 未設＝維持開放（本地開發用）
CREATE_KEY = os.environ.get("CREATE_KEY") or ""  # 自助開庫碼；未設＝自助開庫關閉
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
        cur.execute("CREATE TABLE IF NOT EXISTS banks ("
                    "slug TEXT PRIMARY KEY, name TEXT, text TEXT NOT NULL DEFAULT '', "
                    "title TEXT DEFAULT '', subtitle TEXT DEFAULT '', key_hash TEXT, "
                    "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        cur.execute("ALTER TABLE banks ADD COLUMN IF NOT EXISTS created_ip TEXT")
        cur.execute("ALTER TABLE banks ADD COLUMN IF NOT EXISTS owner_id INT")
        cur.execute("CREATE TABLE IF NOT EXISTS users ("
                    "id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, "
                    "pass_hash TEXT NOT NULL, salt TEXT NOT NULL, "
                    "created_at TEXT NOT NULL, bank_slug TEXT)")
        # 舊 /api/session 遺留嘅 sessions 表用唔到（id/mode/rounds…），另開 auth_sessions
        cur.execute("CREATE TABLE IF NOT EXISTS auth_sessions ("
                    "token_hash TEXT PRIMARY KEY, user_id INT NOT NULL, "
                    "created_at TEXT NOT NULL, expires_at TEXT NOT NULL)")
        # 一次性遷移：舊嘅單一題庫（meta.text）搬入 slug='default'
        cur.execute("SELECT 1 FROM banks WHERE slug='default'")
        if not cur.fetchone():
            cur.execute("SELECT value FROM meta WHERE key='text'")
            row = cur.fetchone()
            base = row["value"] if row else None
            base = base if base is not None else seed_text()
            cur.execute("SELECT value FROM meta WHERE key='title'")
            t = cur.fetchone()
            cur.execute("SELECT value FROM meta WHERE key='subtitle'")
            st = cur.fetchone()
            ts = now()
            cur.execute("INSERT INTO banks (slug,name,text,title,subtitle,key_hash,created_at,updated_at) "
                        "VALUES ('default','預設題庫',%s,%s,%s,NULL,%s,%s)",
                        (base, (t["value"] if t else "") or "", (st["value"] if st else "") or "", ts, ts))


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
    """新用戶題庫的起頭題目：優先 samples/seed.txt（一行一題），否則由舊 JSON 抽。"""
    plain = os.path.join(ROOT, "samples", "seed.txt")
    if os.path.exists(plain):
        with open(plain, encoding="utf-8") as f:
            rows = [ln.strip() for ln in f if ln.strip()]
        if rows:
            return "\n".join(rows)
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


def get_bank(cur, slug):
    cur.execute("SELECT slug,name,text,title,subtitle,key_hash,updated_at FROM banks WHERE slug=%s", (slug,))
    return cur.fetchone()


def bank_key_ok(request, bank):
    """master（EDIT_KEY）可改任何題庫；otherwise 比對該題庫自己的密碼 hash。"""
    supplied = request.headers.get("x-edit-key", "")
    if EDIT_KEY and supplied == EDIT_KEY:
        return True
    if not EDIT_KEY and not (bank and bank.get("key_hash")):
        return True                                   # 本地開發：完全開放
    h = (bank or {}).get("key_hash")
    return bool(h) and hashlib.sha256(supplied.encode()).hexdigest() == h


def read_text(cur):
    """舊路徑兼容：回 default 題庫內文。"""
    row = get_bank(cur, "default")
    if row:
        return row["text"]
    text = get_meta(cur, "text")
    if text is None:
        text = seed_text()
        put_meta(cur, "text", text)
        put_meta(cur, "updated_at", now())
    return text


# ------------------------------------------------------------------ routes
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
USER_RE = re.compile(r"^[a-z0-9_.\-]{3,24}$")


def hash_pw(pw, salt):
    return hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32).hex()


def new_salt():
    return secrets.token_hex(16)


def issue_token(cur, user_id):
    tok = secrets.token_urlsafe(32)
    ts = datetime.now(timezone.utc)
    cur.execute("INSERT INTO auth_sessions (token_hash,user_id,created_at,expires_at) VALUES (%s,%s,%s,%s)",
                (hashlib.sha256(tok.encode()).hexdigest(), user_id, ts.isoformat(timespec="seconds"),
                 (ts + timedelta(days=30)).isoformat(timespec="seconds")))
    return tok


def session_user(request):
    """由 Authorization: Bearer <token> 認人；回 users row（dict）或 None。"""
    auth = request.headers.get("authorization", "")
    tok = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not tok:
        return None
    h = hashlib.sha256(tok.encode()).hexdigest()
    with db() as (c, cur):
        cur.execute("SELECT u.id,u.username,u.bank_slug FROM auth_sessions s JOIN users u ON u.id=s.user_id "
                    "WHERE s.token_hash=%s AND s.expires_at > %s", (h, now()))
        return cur.fetchone()


def user_bank(cur, user):
    slug = user.get("bank_slug")
    if slug:
        cur.execute("SELECT slug,name,text,key_hash,owner_id,updated_at FROM banks WHERE slug=%s", (slug,))
        row = cur.fetchone()
        if row:
            return row
    # 保險：未綁定就綁一份
    cur.execute("SELECT slug,name FROM banks WHERE owner_id=%s ORDER BY created_at LIMIT 1", (user["id"],))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE users SET bank_slug=%s WHERE id=%s", (row["slug"], user["id"]))
        return row
    return None


def norm_slug(b):
    b = (b or "default").strip().lower()
    return b if SLUG_RE.match(b) else "default"


def key_ok(request):
    """未設 EDIT_KEY 就唔檢查（本地開發／未配置環境變數時保持可用）。"""
    if not EDIT_KEY:
        return True
    return request.headers.get("x-edit-key", "") == EDIT_KEY


@app.post("/api/signup")
async def signup(request: Request):
    body = await request.json()
    username = str(body.get("username") or "").strip().lower()
    pw = str(body.get("password") or "")
    code = str(body.get("code") or "")
    if CREATE_KEY and not secrets.compare_digest(code, CREATE_KEY):
        return JSONResponse({"error": "邀請碼不正確"}, status_code=401)
    if not USER_RE.match(username):
        return JSONResponse({"error": "用戶名 3-24 個字，只可用細楷英數、_ . -"}, status_code=400)
    if len(pw) < 6:
        return JSONResponse({"error": "密碼至少 6 個字"}, status_code=400)
    salt = new_salt()
    schema()
    with db() as (c, cur):
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return JSONResponse({"error": "用戶名已被使用"}, status_code=409)
        # 每人都有一份自己嘅題庫：用預設題目起頭，玩得到先，再自己改
        slug = _new_slug(cur)
        ts = now()
        cur.execute("INSERT INTO banks (slug,name,text,title,subtitle,key_hash,created_at,updated_at) "
                    "VALUES (%s,%s,%s,'','',NULL,%s,%s)",
                    (slug, username, seed_text(), ts, ts))
        cur.execute("INSERT INTO users (username,pass_hash,salt,created_at,bank_slug) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (username, hash_pw(pw, salt), salt, ts, slug))
        cur.execute("SELECT id,username,bank_slug FROM users WHERE username=%s", (username,))
        u = cur.fetchone()
        cur.execute("UPDATE banks SET owner_id=%s WHERE slug=%s", (u["id"], slug))
        tok = issue_token(cur, u["id"])
    return {"ok": True, "token": tok, "user": {"username": username}, "bank": {"slug": slug, "name": username}}


@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    username = str(body.get("username") or "").strip().lower()
    pw = str(body.get("password") or "")
    schema()
    with db() as (c, cur):
        cur.execute("SELECT id,username,pass_hash,salt,bank_slug FROM users WHERE username=%s", (username,))
        u = cur.fetchone()
        if not u or not secrets.compare_digest(hash_pw(pw, u["salt"]), u["pass_hash"]):
            return JSONResponse({"error": "用戶名或密碼不正確"}, status_code=401)
        bank = user_bank(cur, u)
        tok = issue_token(cur, u["id"])
    return {"ok": True, "token": tok, "user": {"username": u["username"]},
            "bank": {"slug": (bank or {}).get("slug"), "name": (bank or {}).get("name")}}


@app.post("/api/logout")
def logout(request: Request):
    auth = request.headers.get("authorization", "")
    tok = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if tok:
        with db() as (c, cur):
            cur.execute("DELETE FROM auth_sessions WHERE token_hash=%s",
                        (hashlib.sha256(tok.encode()).hexdigest(),))
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    user = session_user(request)
    if not user:
        return JSONResponse({"error": "未登入"}, status_code=401)
    with db() as (c, cur):
        bank = user_bank(cur, user)
    return {"ok": True, "user": {"username": user["username"]},
            "bank": {"slug": (bank or {}).get("slug"), "name": (bank or {}).get("name"),
                     "chars": len((bank or {}).get("text") or "")}}


@app.get("/api/banks")
def banks_list(request: Request):
    """只俾 master 睇：邊個開過幾多份題庫。"""
    if not key_ok(request):
        return JSONResponse({"error": "未授權"}, status_code=401)
    schema()
    with db() as (c, cur):
        cur.execute("SELECT slug,name,title,subtitle,length(text) AS chars,updated_at,"
                    "(key_hash IS NOT NULL) AS locked FROM banks ORDER BY created_at")
        rows = [dict(r) for r in cur.fetchall()]
    return {"ok": True, "count": len(rows), "items": rows}


@app.post("/api/banks")
async def banks_create(request: Request):
    """開新題庫：要有 master key。可順便設該題庫自己的密碼（key）。"""
    if not key_ok(request):
        return JSONResponse({"error": "未授權"}, status_code=401)
    body = await request.json()
    slug = (body.get("slug") or "").strip().lower()
    if not SLUG_RE.match(slug):
        return JSONResponse({"error": "slug 只可以用細楷英數同連字號（2-32 字）"}, status_code=400)
    text = body.get("text") or ""
    if not isinstance(text, str):
        return JSONResponse({"error": "text 要係字串"}, status_code=400)
    text = text.replace("\r\n", "\n").replace("\r", "\n")[:200000]
    name = (body.get("name") or slug).strip()[:40]
    key = body.get("key") or ""
    ts = now()
    schema()
    with db() as (c, cur):
        if get_bank(cur, slug):
            return JSONResponse({"error": "slug 已存在"}, status_code=409)
        cur.execute("INSERT INTO banks (slug,name,text,title,subtitle,key_hash,created_at,updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (slug, name, text, (body.get("title") or "")[:24], (body.get("subtitle") or "")[:36],
                     hashlib.sha256(key.encode()).hexdigest() if key else None, ts, ts))
    return {"ok": True, "slug": slug, "url": f"/b/{slug}", "edit": f"/edit?b={slug}"}


def _new_slug(cur):
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    for _ in range(12):
        cand = "".join(secrets.choice(alphabet) for _ in range(6))
        cur.execute("SELECT 1 FROM banks WHERE slug=%s", (cand,))
        if not cur.fetchone():
            return cand
    raise RuntimeError("slug 生成失敗，再試一次")


@app.post("/api/newbank")
async def banks_selfserve(request: Request):
    """自助開庫：要 CREATE_KEY。每位來源每日最多 5 份，總數上限 120 份。"""
    if not CREATE_KEY:
        return JSONResponse({"error": "自助開庫未啟用"}, status_code=503)
    body = await request.json()
    code = str(body.get("code") or "")
    if not secrets.compare_digest(code, CREATE_KEY):
        return JSONResponse({"error": "開庫碼不正確"}, status_code=401)
    name = str(body.get("name") or "").strip()[:40]
    if not name:
        return JSONResponse({"error": "請填題庫名稱"}, status_code=400)
    key = str(body.get("key") or "")
    if len(key) < 4:
        return JSONResponse({"error": "密碼至少 4 個字"}, status_code=400)
    text = body.get("text") or ""
    if not isinstance(text, str):
        return JSONResponse({"error": "text 要係字串"}, status_code=400)
    text = text.replace("\r\n", "\n").replace("\r", "\n")[:200000]
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or request.headers.get("x-real-ip", "") or "")
    schema()
    with db() as (c, cur):
        cur.execute("SELECT count(*) AS n FROM banks")
        if cur.fetchone()["n"] >= 120:
            return JSONResponse({"error": "題庫數量已滿，請聯絡管理員"}, status_code=429)
        cur.execute("SELECT count(*) AS n FROM banks WHERE created_ip=%s AND created_at >= %s",
                    (ip, now()[:10]))
        if cur.fetchone()["n"] >= 5:
            return JSONResponse({"error": "今日開庫次數已用完（每日 5 份）"}, status_code=429)
        slug = _new_slug(cur)
        ts = now()
        cur.execute("INSERT INTO banks (slug,name,text,title,subtitle,key_hash,created_at,updated_at,created_ip) "
                    "VALUES (%s,%s,%s,'','',%s,%s,%s,%s)",
                    (slug, name, text, hashlib.sha256(key.encode()).hexdigest(), ts, ts, ip))
    return {"ok": True, "slug": slug, "name": name,
            "play": f"/b/{slug}", "edit": f"/edit?b={slug}"}


@app.post("/api/findbank")
async def find_bank(request: Request):
    """用戶唔記得連結：用「題庫名稱 + 密碼」搵返 slug（名稱可以重複，逐個試）。"""
    body = await request.json()
    name = str(body.get("name") or "").strip()
    key = str(body.get("key") or "")
    if not name or not key:
        return JSONResponse({"error": "請填題庫名稱同密碼"}, status_code=400)
    schema()
    h = hashlib.sha256(key.encode()).hexdigest()
    with db() as (c, cur):
        cur.execute("SELECT slug,name,key_hash FROM banks WHERE lower(name)=lower(%s)", (name,))
        rows = cur.fetchall()
    hits = [{"slug": r["slug"], "name": r["name"]} for r in rows if r["key_hash"] == h]
    if not hits:
        return JSONResponse({"error": "名稱或密碼不正確"}, status_code=401)
    return {"ok": True, "count": len(hits), "items": hits}


@app.get("/api/text")
def text_get(request: Request, check: int = 0, b: str = "default"):
    slug = norm_slug(b)
    if check:                                   # 只驗密碼，唔讀題庫內容
        schema()
        with db() as (c, cur):
            bank = get_bank(cur, slug)
        if bank is None:
            return JSONResponse({"error": "找不到題庫"}, status_code=404)
        return {"ok": bank_key_ok(request, bank), "protected": bool(bank.get("key_hash") or EDIT_KEY)}
    schema()
    with db() as (c, cur):
        bank = get_bank(cur, slug)
        if bank is None:
            return JSONResponse({"error": "找不到題庫"}, status_code=404)
        return {"slug": bank["slug"], "name": bank["name"] or bank["slug"],
                "text": bank["text"], "title": bank["title"] or "",
                "subtitle": bank["subtitle"] or "", "updated_at": bank["updated_at"]}


@app.put("/api/text")
async def text_put(request: Request, b: str = "default"):
    schema()
    slug = norm_slug(b)
    with db() as (c, cur):
        bank = get_bank(cur, slug)
    if bank is None:
        return JSONResponse({"error": "找不到題庫"}, status_code=404)
    user = session_user(request)
    owns = bool(user and (bank.get("owner_id") == user["id"] or user.get("bank_slug") == slug))
    if not owns and not bank_key_ok(request, bank):
        return JSONResponse({"error": "未授權"}, status_code=401)
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
        cur.execute("UPDATE banks SET text=%s, updated_at=%s WHERE slug=%s", (text, now(), slug))
        if title is not None:
            cur.execute("UPDATE banks SET title=%s WHERE slug=%s", (title.strip()[:24], slug))
        if subtitle is not None:
            cur.execute("UPDATE banks SET subtitle=%s WHERE slug=%s", (subtitle.strip()[:36], slug))
        cur.execute("UPDATE banks SET updated_at=%s WHERE slug=%s", (now(), slug))
    return {"ok": True, "slug": slug, "chars": len(text)}


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
