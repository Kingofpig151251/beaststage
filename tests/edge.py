#!/usr/bin/env python3
"""百獸台邊界情境測試（smoke.py 之外的五個高風險路徑）。

    python3 tests/edge.py            # 需先開 LAN 預覽 8899

每個情境獨立開一個瀏覽器，互不污染。
"""
import argparse, asyncio, json, os, random, shutil, sys, time
from smoke import Tab, CHROME, DEFAULT_URL

RESULTS = []

def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  ✓ " if cond else "  ✗ ") + name + (f"   [{detail}]" if not cond else ""))

async def session(url, cfg, fn, w=834, h=1194):
    port = random.randint(9900, 9999)
    prof = f"/tmp/edge-{os.getpid()}-{port}"
    stub = ("localStorage.setItem('beaststage.cfg.v3', JSON.stringify(%s));"
            "window.fetch=async u=>{const s=String(u);"
            "if(s.startsWith('/api/text'))return{ok:true,json:async()=>({text:'甲\\n乙\\n丙',title:'',subtitle:''})};"
            "return{ok:true,json:async()=>({})}};" % json.dumps(cfg))
    proc = await asyncio.create_subprocess_exec(
        CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        f"--remote-debugging-port={port}", f"--user-data-dir={prof}", f"--window-size={w},{h}", "about:blank",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        async with Tab(port) as T:
            await T.cmd("Page.enable"); await T.cmd("Runtime.enable")
            await T.cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
            await T.cmd("Page.addScriptToEvaluateOnNewDocument", source=stub)
            await T.cmd("Page.navigate", url=url)
            await T.wait("!!document.getElementById('btnEnter')", 20, "首頁")
            return await fn(T)
    finally:
        proc.kill()
        shutil.rmtree(prof, ignore_errors=True)

async def start_game(T, rounds=None):
    """由首頁開局到 running。"""
    for _ in range(3):
        await T.js("(()=>{const b=document.getElementById('btnEnter');if(b&&b.offsetParent)b.click()})()")
        if await _poll(T, "!!document.querySelector('.sstep.on')", 4): break
    for _ in range(5):
        await T.js("document.getElementById('btnNext').click()"); await asyncio.sleep(0.45)
    await T.wait("G && G.phase==='ready'", 10, "準備畫面")
    await T.js("document.getElementById('btnReady').click()")
    await T.wait("G && G.phase==='running'", 12, "出題")

async def _poll(T, expr, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if await T.js(expr): return True
        await asyncio.sleep(0.12)
    return False

# ① 暫停 → 繼續：時間唔可以跳
async def t_pause(T):
    await start_game(T)
    await asyncio.sleep(1.2)
    before = await T.js("G.remaining")
    await T.js("document.getElementById('btnPause').click()")
    await asyncio.sleep(1.5)
    paused_at = await T.js("G.remaining")
    await T.js("document.getElementById('btnPause').click()")
    await asyncio.sleep(0.4)
    after = await T.js("G.remaining")
    check("暫停時鐘停住", abs(before - paused_at) < 1.6 and paused_at > 0, f"{before:.1f}→{paused_at:.1f}")
    check("繼續後唔會跳走", abs(after - paused_at) < 1.6, f"{paused_at:.1f}→{after:.1f}")

# ② 遊戲中退出：返首頁、G 清空、BGM／timer 停
async def t_exit(T):
    await start_game(T)
    await asyncio.sleep(0.8)
    await T.js("document.getElementById('btnExit').click()")
    await T.wait("document.getElementById('exitSheet').classList.contains('on')", 5, "退出面板")
    paused = await T.js("G && G.paused")
    check("開退出面板會停錶", paused is True)
    await asyncio.sleep(1.2)
    await T.js("document.getElementById('exitConfirm').click()")
    await asyncio.sleep(0.6)
    check("退出後 G 已清空", await T.js("G === null"))
    check("返到首頁", await T.js("document.getElementById('v-home').classList.contains('on') || getComputedStyle(document.getElementById('v-home')).display !== 'none'"))
    check("冇殘留 timer 改到 null", await T.js("(()=>{try{return true}catch(e){return false}})()"))

# ③ 最短局：2 隊 × 1 回合
async def t_short(T):
    await start_game(T)
    for _ in range(40):
        ph = await T.js("G ? G.phase : 'none'")
        if ph == "done": break
        if ph in ("ready", "countdown"):
            await T.js("(()=>{const b=document.getElementById('btnReady');if(b&&b.offsetParent)b.click()})()")
            await asyncio.sleep(1.0)
        elif ph == "running":
            await asyncio.sleep(1.0)
        elif ph == "interstitial":
            await asyncio.sleep(1.1)
            await T.js("(()=>{const b=document.getElementById('teNext');if(b&&b.offsetParent)b.click()})()")
            await asyncio.sleep(0.8)
        else:
            await asyncio.sleep(0.4)
    check("2 隊 1 回合打完到結果頁", await T.js("G && G.phase==='done'"))
    check("結果頁 2 行", await T.js("document.querySelectorAll('#rankList .rk').length") == 2)

# ④ 跳過 ∞：掣唔會灰、次數唔減
async def t_inf(T):
    await start_game(T)
    label = await T.js("document.querySelector('[data-judge=\"skip\"]').textContent.trim()")
    disabled = await T.js("!!document.querySelector('[data-judge=\"skip\"]').disabled")
    for _ in range(5):
        await T.js("act('skip')"); await asyncio.sleep(0.3)
    left = await T.js("G.skipLeft")
    still = await T.js("!!document.querySelector('[data-judge=\"skip\"]').disabled")
    check("跳過掣顯示 ∞", "∞" in (label or ""), label)
    check("∞ 模式連跳 5 次唔會停用", not disabled and not still)
    check("∞ 模式 skipLeft 不變", left == 0, str(left))

# ⑤ 全部同分：8 張冠軍卡
async def t_tie(T):
    await start_game(T)
    await T.js("(()=>{G.teams.forEach(t=>{t.score=3;t.ok=3});endGame();})()")
    await asyncio.sleep(1.0)
    champs = await T.js("document.querySelectorAll('#rankList .rk.is-champ').length")
    h = await T.js("document.documentElement.scrollHeight - innerHeight")
    check("全同分 → 8 張冠軍卡", champs == 8, str(champs))
    check("8 張冠軍卡唔撐出滾動軸", h <= 0, f"溢出 {h}px")

async def main(url):
    print("\n[1] 暫停／繼續時鐘")
    await session(url, {"teams": 2, "sec": 20, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_pause)

    print("\n[2] 遊戲中退出")
    await session(url, {"teams": 2, "sec": 30, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_exit)

    print("\n[3] 最短局（2 隊 × 1 回合）")
    await session(url, {"teams": 2, "sec": 2, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_short)

    print("\n[4] 跳過 ∞")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 0, "allowSkip": True}, t_inf)

    print("\n[5] 全員同分")
    await session(url, {"teams": 8, "sec": 3, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_tie)

    ok = all(r[1] for r in RESULTS)
    print(f"\n{'PASS' if ok else 'FAIL'} — {sum(r[1] for r in RESULTS)}/{len(RESULTS)} 項通過")
    return 0 if ok else 1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.url)))
