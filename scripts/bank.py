#!/usr/bin/env python3
"""題庫（bank）管理小工具 —— 只係打 prod API，唔直接碰 DB。

    python3 scripts/bank.py list
    python3 scripts/bank.py new <slug> "<名稱>" [--key <該題庫密碼>] [--from default]
    python3 scripts/bank.py text <slug>                # 印出該題庫內容
    python3 scripts/bank.py rm <slug>                  # 只刪 DB 記錄（工具自己用，API 冇 DELETE）

Master key 由 .env.local 的 EDIT_KEY 讀（600；已 gitignore）。
"""
import argparse, json, os, sys, urllib.request, urllib.error

BASE = os.environ.get("BEASTTV_BASE", "https://beasttv.vercel.app")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def master_key():
    k = os.environ.get("EDIT_KEY")
    if k:
        return k
    env = os.path.join(ROOT, ".env.local")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            if line.startswith("EDIT_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("找不到 EDIT_KEY（環境變數或 .env.local）")


def call(path, method="GET", body=None, key=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("x-edit-key", key or master_key())
    if body is not None:
        req.add_header("content-type", "application/json")
        req.data = json.dumps(body, ensure_ascii=False).encode()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"{e.code} {e.read().decode(errors='replace')[:200]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_new = sub.add_parser("new")
    p_new.add_argument("slug")
    p_new.add_argument("name")
    p_new.add_argument("--key", default="")
    p_new.add_argument("--from", dest="src", default="")
    p_text = sub.add_parser("text")
    p_text.add_argument("slug")
    p_rm = sub.add_parser("rm")
    p_rm.add_argument("slug")
    a = ap.parse_args()

    if a.cmd == "list":
        d = call("/api/banks")
        for it in d["items"]:
            lock = "🔒" if it["locked"] else "  "
            print(f'{it["slug"]:<18} {lock} {it["chars"]:>6} 字  {it["name"]}  ({it["updated_at"]})')
        return

    if a.cmd == "new":
        text = call(f"/api/text?b={a.src}")["text"] if a.src else ""
        d = call("/api/banks", "POST", {"slug": a.slug, "name": a.name, "text": text,
                                        "key": a.key or ""})
        print(f'✓ 開好：{BASE}/b/{d["slug"]}   設定頁：{BASE}{d["edit"]}')
        return

    if a.cmd == "text":
        d = call(f"/api/text?b={a.slug}")
        print(d["text"])
        return

    if a.cmd == "rm":
        # API 冇 DELETE（刻意）：直接用 DATABASE_URL 落 SQL
        import psycopg
        url = os.environ.get("DATABASE_URL") or ""
        if not url:
            for line in open(os.path.join(ROOT, ".env.local"), encoding="utf-8"):
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
        with psycopg.connect(url) as c, c.cursor() as cur:
            cur.execute("DELETE FROM banks WHERE slug=%s", (a.slug,))
            print(f"✓ 刪除 {a.slug}（{cur.rowcount} 行）")


if __name__ == "__main__":
    main()
