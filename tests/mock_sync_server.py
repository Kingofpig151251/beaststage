"""本地 mock 後端：模擬 /api/text（GET/PUT），用嚟開發前端。"""
import json, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

TEXT = "雞蛋仔\n菠蘿包\n絲襪奶茶\n尖沙咀鐘樓\n山頂纜車"


class H(SimpleHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/text"):
            return self._json({"text": TEXT, "updated_at": "now"})
        if self.path.startswith("/api/ping"):
            return self._json({"ok": True})
        return super().do_GET()

    def do_PUT(self):
        global TEXT
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        TEXT = body.get("text") or ""
        return self._json({"ok": True, "chars": len(TEXT)})


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
    host = os.environ.get("MOCK_HOST", "127.0.0.1")      # 0.0.0.0 = 容許同網段機睇預覽
    port = int(os.environ.get("MOCK_PORT", "8899"))
    ThreadingHTTPServer((host, port), H).serve_forever()
