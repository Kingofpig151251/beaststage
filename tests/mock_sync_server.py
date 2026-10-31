"""本地 mock 後端：模擬 /api/login 同 /api/bank（GET/PUT），用嚟測題庫同步，唔使真 PIN。"""
import json, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PIN = "1234"
TOK = "mock-token"
BANK = {"name": "共用題庫", "decks": [
    {"id": "food", "name": "港式小食", "items": [{"t": "雞蛋仔"}, {"t": "菠蘿包"}]},
    {"id": "place", "name": "香港地標", "items": [{"t": "尖沙咀鐘樓"}]},
]}


class H(SimpleHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/bank"):
            return self._json(BANK)
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path.startswith("/api/login"):
            if body.get("pin") == PIN:
                return self._json({"token": TOK, "expires_in": 3600})
            return self._json({"error": "bad pin"}, 401)
        return self._json({"error": "nope"}, 404)

    def do_PUT(self):
        global BANK
        # 開放寫入：唔檢查 token
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        BANK = {"name": body.get("name") or "共用題庫", "decks": body.get("decks") or []}
        return self._json({"ok": True, "decks": len(BANK["decks"])})


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
    ThreadingHTTPServer(("127.0.0.1", 8899), H).serve_forever()
