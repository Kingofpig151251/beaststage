#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大電視 · 後端（題庫管理 + 排行榜）
只用 Python 標準庫 + SQLite，無需 pip install。

用法：
    BIGTV_PIN=2468 python3 server.py
    → http://localhost:8080        （主持台）
    → http://localhost:8080/admin  （後台管理題庫／排行榜）

環境變數：
    BIGTV_PORT  監聽端口（預設 8080）
    BIGTV_HOST  監聽地址（預設 0.0.0.0）
    BIGTV_DB    SQLite 路徑（預設 ./data/bigtv.db）
    BIGTV_PIN   後台密碼（預設 2468，正式用一定要改）
"""

import json
import os
import re
import sqlite3
import secrets
import hmac
import threading
import time
import mimetypes
import urllib.parse
from contextlib import contextmanager
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BIGTV_DB", os.path.join(ROOT, "data", "bigtv.db"))
ADMIN_PIN = os.environ.get("BIGTV_PIN", "2468")
PORT = int(os.environ.get("BIGTV_PORT", "8080"))
HOST = os.environ.get("BIGTV_HOST", "0.0.0.0")
SEED = os.path.join(ROOT, "samples", "hk-icebreaker.json")
TOKEN_TTL = 12 * 3600
MAX_BODY = 2 * 1024 * 1024

_lock = threading.Lock()
_tokens = {}   # token -> expiry epoch


# ---------------------------------------------------------------- database

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def conn_ctx():
    """commit + close，唔會漏 connection。"""
    c = db()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with conn_ctx() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS decks (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, sort INTEGER DEFAULT 0,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id TEXT NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
            text TEXT NOT NULL, sort INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_items_deck ON items(deck_id);
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finished_at TEXT NOT NULL, mode TEXT, rounds INTEGER,
            questions INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            player TEXT NOT NULL, score INTEGER DEFAULT 0,
            ok INTEGER DEFAULT 0, skip INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_results_session ON results(session_id);
        CREATE INDEX IF NOT EXISTS idx_results_player ON results(player);
        """)
        # 首次啟動：載入內建香港題庫
        n = conn.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"]
        if n == 0 and os.path.exists(SEED):
            with open(SEED, encoding="utf-8") as f:
                seed = json.load(f)
            for i, d in enumerate(seed.get("decks", [])):
                conn.execute("INSERT OR REPLACE INTO decks(id,name,sort,updated_at) VALUES(?,?,?,?)",
                             (d["id"], d["name"], i, now()))
                for j, it in enumerate(d.get("items", [])):
                    t = (it if isinstance(it, str) else it.get("t", "")).strip()
                    if t:
                        conn.execute("INSERT INTO items(deck_id,text,sort) VALUES(?,?,?)",
                                     (d["id"], t, j))
            conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('name',?)",
                         (seed.get("name", "香港破冰題庫"),))


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_bank(conn=None):
    own = conn is None
    conn = conn or db()
    try:
        name = conn.execute("SELECT value FROM meta WHERE key='name'").fetchone()
        decks = []
        for d in conn.execute("SELECT * FROM decks ORDER BY sort, name"):
            items = [{"id": r["id"], "t": r["text"]}
                     for r in conn.execute(
                         "SELECT id, text FROM items WHERE deck_id=? ORDER BY sort, id", (d["id"],))]
            decks.append({"id": d["id"], "name": d["name"], "items": items})
        return {"name": name["value"] if name else "題庫", "decks": decks,
                "updated_at": conn.execute("SELECT MAX(updated_at) u FROM decks").fetchone()["u"]}
    finally:
        if own:
            conn.close()


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "deck"


def unique_deck_id(conn, base):
    cand, i = base, 2
    while conn.execute("SELECT 1 FROM decks WHERE id=?", (cand,)).fetchone():
        cand = f"{base}-{i}"
        i += 1
    return cand


# ---------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    server_version = "BigTV/1.0"

    # -- helpers -------------------------------------------------
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body=b"", ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype.startswith("application/json") else "no-cache")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _json_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        if n > MAX_BODY:
            raise ValueError("body too large")
        raw = self.rfile.read(n)
        data = json.loads(raw.decode("utf-8") or "{}")
        return data if isinstance(data, dict) else {}

    def _token_ok(self):
        if not ADMIN_PIN:
            return True
        tok = self.headers.get("X-Admin-Token") or ""
        exp = _tokens.get(tok)
        if not exp or exp < time.time():
            return False
        return True

    def _need_auth(self):
        if self._token_ok():
            return True
        self._send(401, {"error": "需要後台登入"})
        return False

    def _static(self, path):
        if path in ("/", "/index.html"):
            path = "/index.html"
        elif path in ("/admin", "/admin.html", "/admin/"):
            path = "/admin.html"
        else:
            path = os.path.normpath("/" + path.lstrip("/"))
        if path.endswith("/"):
            path += "index.html"
        full = os.path.join(ROOT, path.lstrip("/"))
        if not os.path.abspath(full).startswith(ROOT) or not os.path.isfile(full):
            self._send(404, {"error": "not found"})
            return
        ctype, _ = mimetypes.guess_type(full)
        with open(full, "rb") as f:
            data = f.read()
        if ctype in ("text/html", "text/css", "application/javascript"):
            ctype += "; charset=utf-8"
        self._send(200, data, ctype or "application/octet-stream")

    # -- routing -------------------------------------------------
    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        p, q = u.path, urllib.parse.parse_qs(u.query)
        try:
            if p == "/api/ping":
                return self._send(200, {"ok": True, "time": now(), "version": 1})
            if p == "/api/bank":
                with conn_ctx() as conn:
                    return self._send(200, read_bank(conn))
            if p == "/api/leaderboard":
                return self._send(200, self._leaderboard(int((q.get("limit") or ["10"])[0])))
            if p == "/api/sessions":
                return self._send(200, self._sessions(int((q.get("limit") or ["20"])[0])))
            if p.startswith("/api/"):
                return self._send(404, {"error": "unknown endpoint"})
            return self._static(p)
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": str(e)})

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        self._write("POST")

    def do_PATCH(self):
        self._write("PATCH")

    def do_PUT(self):
        self._write("PUT")

    def do_DELETE(self):
        self._write("DELETE")

    def _write(self, method):
        p = urllib.parse.urlsplit(self.path).path
        try:
            body = self._json_body()
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": f"bad json: {e}"})

        try:
            # 登入唔需要 token
            if p == "/api/login" and method == "POST":
                pin = str(body.get("pin", ""))
                if ADMIN_PIN and hmac.compare_digest(pin, ADMIN_PIN):
                    tok = secrets.token_urlsafe(24)
                    _tokens[tok] = time.time() + TOKEN_TTL
                    return self._send(200, {"token": tok, "expires_in": TOKEN_TTL})
                time.sleep(0.4)
                return self._send(403, {"error": "密碼唔對"})
            if p == "/api/logout" and method == "POST":
                _tokens.pop(self.headers.get("X-Admin-Token") or "", None)
                return self._send(200, {"ok": True})

            if p == "/api/sessions" and method == "POST":
                return self._send(200, self._add_session(body))

            # 以下要登入
            if p.startswith("/api/"):
                if not self._need_auth():
                    return

            m = re.fullmatch(r"/api/decks", p)
            if m and method == "POST":
                return self._send(200, self._add_deck(body))
            m = re.fullmatch(r"/api/decks/([^/]+)", p)
            if m:
                if method == "PATCH":
                    return self._send(200, self._rename_deck(m.group(1), body))
                if method == "DELETE":
                    return self._send(200, self._del_deck(m.group(1)))
            m = re.fullmatch(r"/api/decks/([^/]+)/items", p)
            if m and method == "POST":
                return self._send(200, self._add_items(m.group(1), body))
            m = re.fullmatch(r"/api/items/(\d+)", p)
            if m:
                if method == "PATCH":
                    return self._send(200, self._edit_item(int(m.group(1)), body))
                if method == "DELETE":
                    return self._send(200, self._del_item(int(m.group(1))))
            if p == "/api/bank" and method == "PUT":
                return self._send(200, self._replace_bank(body))
            m = re.fullmatch(r"/api/sessions/(\d+)", p)
            if m and method == "DELETE":
                return self._send(200, self._del_session(int(m.group(1))))
            m = re.fullmatch(r"/api/reset", p)
            if m and method == "POST":
                return self._send(200, self._reset(body))

            return self._send(404, {"error": "unknown endpoint"})
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": str(e)})

    # -- business ------------------------------------------------
    def _leaderboard(self, limit=10):
        limit = max(1, min(100, limit))
        with conn_ctx() as conn:
            players = [dict(r) for r in conn.execute("""
                SELECT r.player AS name,
                       SUM(r.score) AS total,
                       MAX(r.score) AS best,
                       COUNT(*) AS games,
                       SUM(r.ok) AS ok, SUM(r.skip) AS skips
                FROM results r
                GROUP BY r.player
                ORDER BY total DESC, best DESC, games DESC
                LIMIT ?""", (limit,))]
            recent = [dict(r) for r in conn.execute("""
                SELECT s.id, s.finished_at, s.mode, s.rounds, s.questions,
                       (SELECT player FROM results WHERE session_id=s.id ORDER BY score DESC, ok DESC LIMIT 1) AS winner,
                       (SELECT score  FROM results WHERE session_id=s.id ORDER BY score DESC, ok DESC LIMIT 1) AS winner_score,
                       (SELECT COUNT(*) FROM results WHERE session_id=s.id) AS players
                FROM sessions s ORDER BY s.id DESC LIMIT ?""", (limit,))]
            total = conn.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"]
        return {"players": players, "recent": recent, "sessions_total": total}

    def _sessions(self, limit=20):
        limit = max(1, min(200, limit))
        with conn_ctx() as conn:
            rows = [dict(r) for r in conn.execute("""
                SELECT id, finished_at, mode, rounds, questions
                FROM sessions ORDER BY id DESC LIMIT ?""", (limit,))]
            for r in rows:
                r["results"] = [dict(x) for x in conn.execute(
                    "SELECT player,score,ok,skip FROM results WHERE session_id=? ORDER BY score DESC", (r["id"],))]
        return {"sessions": rows}

    def _add_session(self, body):
        mode = str(body.get("mode", ""))[:40]
        rounds = int(body.get("rounds") or 0)
        questions = int(body.get("questions") or 0)
        teams = body.get("teams") or []
        if not isinstance(teams, list) or not teams:
            raise ValueError("teams 唔可以空")
        with conn_ctx() as conn, _lock:
            cur = conn.execute(
                "INSERT INTO sessions(finished_at,mode,rounds,questions) VALUES(?,?,?,?)",
                (now(), mode, rounds, questions))
            sid = cur.lastrowid
            for t in teams[:16]:
                player = str(t.get("name", "?"))[:40] or "?"
                conn.execute(
                    "INSERT INTO results(session_id,player,score,ok,skip) VALUES(?,?,?,?,?)",
                    (sid, player, int(t.get("score") or 0), int(t.get("ok") or 0),
                     int(t.get("skip") or 0)))
        return {"id": sid, "ok": True}

    def _add_deck(self, body):
        name = str(body.get("name", "")).strip()
        if not name:
            raise ValueError("類別名唔可以空")
        with conn_ctx() as conn, _lock:
            did = unique_deck_id(conn, slug(body.get("id") or name))
            s = (conn.execute("SELECT COALESCE(MAX(sort),0)+1 s FROM decks").fetchone()["s"])
            conn.execute("INSERT INTO decks(id,name,sort,updated_at) VALUES(?,?,?,?)",
                         (did, name[:40], s, now()))
        return {"id": did, "name": name}

    def _rename_deck(self, did, body):
        name = str(body.get("name", "")).strip()
        if not name:
            raise ValueError("類別名唔可以空")
        with conn_ctx() as conn, _lock:
            conn.execute("UPDATE decks SET name=?, updated_at=? WHERE id=?", (name[:40], now(), did))
        return {"ok": True}

    def _del_deck(self, did):
        with conn_ctx() as conn, _lock:
            conn.execute("DELETE FROM decks WHERE id=?", (did,))
        return {"ok": True}

    def _add_items(self, did, body):
        items = body.get("items") or []
        if not isinstance(items, list):
            raise ValueError("items 要係 array")
        added = 0
        with conn_ctx() as conn, _lock:
            if not conn.execute("SELECT 1 FROM decks WHERE id=?", (did,)).fetchone():
                raise ValueError("類別唔存在")
            s = conn.execute("SELECT COALESCE(MAX(sort),0)+1 s FROM items WHERE deck_id=?",
                             (did,)).fetchone()["s"]
            existing = {r["text"] for r in conn.execute("SELECT text FROM items WHERE deck_id=?", (did,))}
            for it in items[:500]:
                t = (it if isinstance(it, str) else it.get("t", "")).strip()
                if not t or t in existing:
                    continue
                conn.execute("INSERT INTO items(deck_id,text,sort) VALUES(?,?,?)",
                             (did, t[:200], s))
                existing.add(t)
                s += 1
                added += 1
            conn.execute("UPDATE decks SET updated_at=? WHERE id=?", (now(), did))
        return {"added": added}

    def _edit_item(self, iid, body):
        with conn_ctx() as conn, _lock:
            row = conn.execute("SELECT * FROM items WHERE id=?", (iid,)).fetchone()
            if not row:
                raise ValueError("題目唔存在")
            t = str(body.get("t", row["text"])).strip()[:200] or row["text"]
            conn.execute("UPDATE items SET text=? WHERE id=?", (t, iid))
            conn.execute("UPDATE decks SET updated_at=? WHERE id=?", (now(), row["deck_id"]))
        return {"ok": True}

    def _del_item(self, iid):
        with conn_ctx() as conn, _lock:
            row = conn.execute("SELECT deck_id FROM items WHERE id=?", (iid,)).fetchone()
            conn.execute("DELETE FROM items WHERE id=?", (iid,))
            if row:
                conn.execute("UPDATE decks SET updated_at=? WHERE id=?", (now(), row["deck_id"]))
        return {"ok": True}

    def _replace_bank(self, body):
        decks = body.get("decks")
        if not isinstance(decks, list):
            raise ValueError("decks 要係 array")
        with conn_ctx() as conn, _lock:
            conn.execute("DELETE FROM items")
            conn.execute("DELETE FROM decks")
            if body.get("name"):
                conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('name',?)",
                             (str(body["name"])[:60],))
            for i, d in enumerate(decks[:60]):
                did = unique_deck_id(conn, slug(d.get("id") or d.get("name")))
                conn.execute("INSERT INTO decks(id,name,sort,updated_at) VALUES(?,?,?,?)",
                             (did, str(d.get("name", did))[:40], i, now()))
                for j, it in enumerate(d.get("items", [])[:800]):
                    t = (it if isinstance(it, str) else it.get("t", "")).strip()
                    if not t:
                        continue
                    conn.execute("INSERT INTO items(deck_id,text,sort) VALUES(?,?,?)",
                                 (did, t[:200], j))
        return {"ok": True, "decks": len(decks)}

    def _del_session(self, sid):
        with conn_ctx() as conn, _lock:
            conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
        return {"ok": True}

    def _reset(self, body):
        what = body.get("what", "")
        with conn_ctx() as conn, _lock:
            if what == "sessions":
                conn.execute("DELETE FROM results")
                conn.execute("DELETE FROM sessions")
            elif what == "bank":
                conn.execute("DELETE FROM items")
                conn.execute("DELETE FROM decks")
        return {"ok": True}


def main():
    init_db()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"大電視 server → http://{HOST}:{PORT}  (後台 /admin，PIN={'已設定' if ADMIN_PIN else '無'}）")
    print(f"DB: {DB_PATH}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
