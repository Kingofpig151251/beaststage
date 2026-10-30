# 第二個入口：部分部署環境會將 /api/a/b 這類深路徑 rewrite 到單一函數
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _app import app  # noqa: E402,F401
