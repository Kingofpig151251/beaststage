#!/usr/bin/env python3
"""Static preview of the result screen, built from index.html's own CSS.

Usage: python3 tests/preview_result.py <width> <height> <out.png>
Prints layout metrics and writes a screenshot (chrome-headless-shell, no harness).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

W, H, OUT = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
SRC = os.path.join(os.path.dirname(__file__), "..", "index.html")
CHROME = "/opt/data/tools/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell"

html = open(SRC, encoding="utf-8").read()
style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)

icons = {}
m = re.search(r"const ICONS = \{(.*?)\n\};", html, re.S)
if m:
    for km in re.finditer(r"(\w+):\s*`([^`]+)`", m.group(1)):
        icons[km.group(1)] = km.group(2)

TEAMS = [
    ("turtle", "烏龜隊", "#34C759", 8, 0, 16),
    ("fox", "狐狸隊", "#FF9500", 7, 1, 13),
    ("whale", "鯨魚隊", "#0071E3", 6, 2, 10),
    ("octopus", "章魚隊", "#AF52DE", 5, 3, 7),
    ("bee", "蜜蜂隊", "#F5A300", 4, 4, 4),
]
CROWN = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 8.4a1 1 0 0 1 1.6-.8L8.3 10.6'
         ' 11.2 5a1 1 0 0 1 1.6 0l2.9 5.6 3.7-3a1 1 0 0 1 1.6.8v8.1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>')

rows = []
for i, (tid, name, color, ok, skip, score) in enumerate(TEAMS):
    champ = i == 0
    rows.append(f'''
    <div class="rk in {'is-champ flipped' if champ else ''}" data-champ="{1 if champ else 0}" style="--tc:{color}">
      <div class="flip">
        <div class="face front"><div class="front-card"></div></div>
        <div class="face back">
          <div class="no">{i + 1}</div>
          <div class="rk-tile"><span class="rk-mark">{icons.get(tid, "")}</span></div>
          <div class="nm"><span class="crown">{CROWN}{'冠軍' if champ else ''}</span>{name}
            <div class="st">對 {ok} · 跳過 {skip} · 犯規 0</div>
          </div>
          <div class="pt" data-score="{score}">{score}</div>
        </div>
      </div>
    </div>''')

MEASURE = """
<script>
window.addEventListener("load", () => {
  const r = el => { const b = el.getBoundingClientRect();
    return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; };
  const card = document.querySelector(".rk.is-champ");
  const back = card.querySelector(".face.back");
  const row2 = document.querySelectorAll(".rk")[1];
  const out = {
    card: r(card), back: r(back),
    tile: r(card.querySelector(".rk-tile")),
    nm: r(card.querySelector(".nm")),
    pt: r(card.querySelector(".pt")),
    crown: r(card.querySelector(".crown")),
    row2: r(row2), row2pt: r(row2.querySelector(".pt")),
    display: getComputedStyle(back).display,
    justify: getComputedStyle(back).justifyContent,
    docH: document.documentElement.scrollHeight
  };
  document.title = JSON.stringify(out);
  document.getElementById("m").textContent = JSON.stringify(out);
});
</script>
"""

page = (
    '<!doctype html><html class="js"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    f"<style>{style}</style></head><body data-view=\"result\"><div class=\"wrap\">"
    '<section class="view active" id="v-result">'
    '<div class="res-head"><h1>最終排名</h1>'
    '<p class="kv" id="rSub" style="margin:8px 0 0">全場答對 30 題 · 總分 50</p></div>'
    f'<div class="rank" id="rankList">{"".join(rows)}</div>'
    '<div class="result-actions on"><button class="btn-primary btn-big" id="btnBackHome">返回主頁</button></div>'
    "</section></div>"
    '<pre id="m" style="font:11px monospace;color:#444;padding:6px"></pre>'
    + MEASURE
    + "</body></html>"
)

tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8", dir="/tmp")
tmp.write(page)
tmp.close()

res = subprocess.run(
    [CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
     f"--window-size={W},{H}", "--force-device-scale-factor=1",
     "--virtual-time-budget=1200", "--dump-dom", f"file://{tmp.name}"],
    capture_output=True, text=True, timeout=90,
)
dom = res.stdout
mm = re.search(r'<pre id="m"[^>]*>(.*?)</pre>', dom, re.S)
if mm and mm.group(1).strip():
    print(json.dumps(json.loads(mm.group(1)), indent=None))

subprocess.run(
    [CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
     f"--window-size={W},{H}", "--force-device-scale-factor=1",
     f"--screenshot={OUT}", f"file://{tmp.name}"],
    capture_output=True, text=True, timeout=90,
)
print(OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "FAIL")
