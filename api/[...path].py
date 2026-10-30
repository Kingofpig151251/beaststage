# Vercel catch-all：/api/* 全部交畀同一個 FastAPI app
# （Vercel 會用檔名 [...] 做 catch-all 路由；實際邏輯喺 _app.py）
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _app import app  # noqa: E402,F401
