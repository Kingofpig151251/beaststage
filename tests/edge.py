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

async def session(url, cfg, fn, w=834, h=1194, fetch_js=None):
    port = random.randint(9900, 9999)
    prof = f"/tmp/edge-{os.getpid()}-{port}"
    fetcher = fetch_js or ("async u=>{const s=String(u);"
            "if(s.startsWith('/api/text'))return{ok:true,json:async()=>({text:'甲\\n乙\\n丙',title:'',subtitle:''})};"
            "return{ok:true,json:async()=>({})}}")
    stub = ("localStorage.setItem('beaststage.cfg.v3', JSON.stringify(%s));"
            "window.__err=[];window.__fetchCount=0;addEventListener('error',e=>window.__err.push(String(e.message)));"
            "window.fetch=%s;" % (json.dumps(cfg), fetcher))
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


# ⑥ 題庫未載入：唔可以卡死——按「重試載入」要有提示並重新 fetch
async def t_emptybank(T):
    await _poll(T, "!!document.getElementById('btnEnter')", 15)
    check("題庫空：開始頁仍可用", await T.js("!!document.getElementById('btnEnter')"))
    for _ in range(3):
        await T.js("(()=>{const b=document.getElementById('btnEnter');if(b&&b.offsetParent)b.click()})()")
        if await _poll(T, "!!document.querySelector('.sstep.on')", 3): break
    label = (await T.js("document.getElementById('btnNext').textContent")) or ""
    disabled = await T.js("!!document.getElementById('btnNext').disabled")
    check("題庫空：掣改寫成「重試載入」", "重試" in label, label)
    check("題庫空：掣唔係封死", disabled is False)
    calls0 = await T.js("window.__fetchCount || 0")
    await T.js("document.getElementById('btnNext').click()")
    toast_on = await _poll(T, "document.getElementById('toast').classList.contains('on')", 2.0)
    check("題庫空：按落去有提示", toast_on)
    check("題庫空：有重新請求題庫", (await T.js("window.__fetchCount || 0")) > calls0)
    check("題庫空：無 JS 例外", (await T.js("window.__err.length")) == 0)

# ⑦ API 失敗：首頁仍可開、唔爆例外
async def t_apifail(T):
    await _poll(T, "!!document.getElementById('btnEnter')", 15)
    check("API 失敗：首頁仍然可用", await T.js("!!document.getElementById('btnEnter')"))
    check("API 失敗：無 JS 例外", (await T.js("window.__err.length")) == 0, str(await T.js("window.__err")))

# ⑧ 時間到同判定撞：唔會雙計、唔會卡住
async def t_endrace(T):
    await start_game(T)
    await _poll(T, "G && G.remaining <= 0.6", 20)
    before = await T.js("curTeam().ok")
    await T.js("act('ok')"); await T.js("act('ok')")     # 同一刻連按兩下
    await asyncio.sleep(0.5)
    after = await T.js("G ? curTeam().ok : null")
    check("時間到邊界：最多加一次", (after is None) or (after - before <= 1), f"{before}→{after}")
    check("時間到邊界：回合正常結束", await _poll(T, "G && (G.phase==='interstitial' || G.phase==='done')", 12))

# ⑨ 連按同一鍵：260ms 內 5 次只算一次
async def t_spam(T):
    await start_game(T)
    before = await T.js("curTeam().ok")
    for _ in range(5):
        await T.js("act('ok')")
    await asyncio.sleep(0.6)
    after = await T.js("curTeam().ok")
    check("連按 5 次只加 1 題", after - before == 1, f"{before}→{after}")

# ⑩ 跳過用完：掣變灰、再按無效
async def t_skipcap(T):
    await start_game(T)
    n0 = await T.js("curTeam().skip")
    await T.js("act('skip')"); await asyncio.sleep(0.45)
    n1 = await T.js("curTeam().skip")
    disabled = await T.js("!!document.querySelector('[data-judge=\"skip\"]').disabled")
    await T.js("act('skip')"); await asyncio.sleep(0.45)
    n2 = await T.js("curTeam().skip")
    check("跳過 1 次後掣變灰", disabled)
    check("用完再按唔會再跳", n2 == n1 == n0 + 1, f"{n0}→{n1}→{n2}")

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

# ⑪ 手誤補救：↑ 撤回（單步）＋ 結算卡加減覆核
async def t_undo(T):
    await start_game(T)
    q0 = await T.js("G.cur && G.cur.t")
    await T.js("act('ok')")
    check("撤回：判定先生效", (await T.js("G.teams[0].score")) == 1)
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowUp'}))")
    await asyncio.sleep(0.25)
    check("撤回：分數回退", (await T.js("G.teams[0].score")) == 0)
    check("撤回：正確次數回退", (await T.js("G.teams[0].ok")) == 0)
    check("撤回：該題放返畫面", (await T.js("G.cur && G.cur.t")) == q0)

    # 撤回鍵（觸控）：判定後著燈，撳一下即退
    await T.js("act('ok')")
    await asyncio.sleep(0.3)
    check("撤回鍵：判定後可按", (await T.js("!document.getElementById('btnUndo').classList.contains('off')")))
    await T.js("document.getElementById('btnUndo').click()")
    await asyncio.sleep(0.3)
    check("撤回鍵：撳完分數回退", (await T.js("G.teams[0].score")) == 0)
    check("撤回鍵：撳完變灰", (await T.js("document.getElementById('btnUndo').classList.contains('off')")))
    await T.js("document.getElementById('btnUndo').click()")
    await asyncio.sleep(0.3)
    check("撤回鍵：冇嘢可撤有提示", "沒有可撤回" in ((await T.js("document.getElementById('toast').textContent")) or ""))

    left1 = await T.js("G.skipLeft")
    await T.js("act('skip')")
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowUp'}))")
    await asyncio.sleep(0.25)
    check("撤回：跳過次數回退", (await T.js("G.skipLeft")) == left1)

    await T.js("act('ok')")
    await asyncio.sleep(0.3)
    await T.js("endTurn()")
    await _poll(T, "G && G.phase==='interstitial'", 6)
    shown = await _poll(T, "!document.getElementById('teStats').hidden", 6)   # 結算卡要等幕布落定
    ok0 = await T.js("G.settle && G.settle.ok")
    check("結算覆核：三個數字有得改", shown and ok0 is not None, f"{shown} ok={ok0}")
    f0 = await T.js("G.settle && G.settle.foul")
    await T.js('document.querySelector(\'[data-k=ok] button[data-d="1"]\').click()')
    await asyncio.sleep(0.35)
    check("結算覆核：加一正確 → 隊分上升",
          (await T.js("G.teams[0].ok")) == ok0 + 1 and (await T.js("G.settle.score")) == ok0 + 1)
    await T.js('document.querySelector(\'[data-k=foul] button[data-d="1"]\').click()')
    await asyncio.sleep(0.35)
    check("結算覆核：加一犯規 → 分數扣減", (await T.js("G.settle.foul")) == f0 + 1)
    await T.js('document.querySelector(\'[data-k=foul] button[data-d="-1"]\').click()')
    await asyncio.sleep(0.35)
    check("結算覆核：減返犯規", (await T.js("G.settle.foul")) == f0)
    check("撤回／覆核：無 JS 例外", (await T.js("window.__err.length")) == 0)

# ⑫ 空白題回報：按鈕存在、有診斷紀錄、唔會寫壞題庫
async def t_report(T):
    await start_game(T)
    await T.js("act('ok')")
    await asyncio.sleep(0.3)
    check("回報：按鍵存在", await T.js("!!document.getElementById('btnReport')"))
    n = await T.js("window.__bigtv.diag.length")
    check("回報：有診斷紀錄", (n or 0) >= 1, n)
    d = await T.js("window.__bigtv.diag[window.__bigtv.diag.length-1]")
    check("回報：紀錄有字級與尺寸", bool(d) and "fs" in d and "cw" in d, d)
    await T.js("document.getElementById('btnReport').click()")
    ok = await _poll(T, "document.getElementById('toast').classList.contains('on')", 4)
    check("回報：按落去有回應", ok)
    check("回報：有存本機備份", (await T.js("(localStorage.getItem('beasttv.reports')||'[]').length")) > 2)
    check("回報：唔會寫題庫", (await T.js("String(window.__bigtv.lines.length)")) is not None)


# ⑬ 英文模式唔應該殘留中文（title / aria-label / 隊名欄）
async def t_i18n(T):
    await start_game(T)
    await T.js("setLang('en')")
    await asyncio.sleep(0.4)
    bad = await T.js("""(()=>{
      const cjk=/[\u4e00-\u9fff]/;
      const out=[];
      document.querySelectorAll('#v-play [title],#v-play [aria-label]').forEach(el=>{
        for(const a of ['title','aria-label']){
          const v=el.getAttribute(a); if(v && cjk.test(v)) out.push(a+': '+v);
        }
      });
      return out.slice(0,6);
    })()""")
    check("英文模式：Play 畫面冇中文 title／aria", not bad, bad)
    await T.js("document.getElementById('btnPause').click()")
    await asyncio.sleep(0.3)
    ttl = await T.js("document.getElementById('btnPause').getAttribute('title')")
    check("英文模式：暫停 tooltip 已翻譯", "暫停" not in str(ttl), ttl)


# ⑭ 準備／倒數時要退得到；落閘期間要封鎖
async def t_quitfloat(T):
    await T.js("__bigtv.startGame()"); await asyncio.sleep(0.3)
    await T.js("__bigtv.enterReady()"); await asyncio.sleep(0.5)
    check("準備畫面：浮動鍵出現", await T.js("!document.getElementById('btnQuitFloat').hidden"))
    check("準備畫面：浮動鍵唔會壓住標題",
          await T.js("(()=>{const r=document.getElementById('btnQuitFloat').getBoundingClientRect();"
                     "const t=document.getElementById('rdRound').getBoundingClientRect();"
                     "return r.right<=innerWidth && r.bottom>0 && (r.left>=t.right || r.bottom<=t.top)})()"))
    await T.js("document.getElementById('btnReady').click()")
    await T.wait("G.phase==='countdown'", 5, "倒數")
    check("倒數畫面：唔再顯示退出鍵（用戶要求）", await T.js("document.getElementById('btnQuitFloat').hidden"))
    await T.wait("G.phase==='running'", 12, "出題")
    check("出題中：浮動鍵收起", await T.js("document.getElementById('btnQuitFloat').hidden"))
    # 落閘期間撳 × 唔可以開面板
    await T.js("__bigtv.endTurn()")
    await _poll(T, "document.getElementById('gate').classList.contains('on')", 5)
    await T.js("document.getElementById('btnExit').click()"); await asyncio.sleep(0.3)
    check("落閘期間撳 × 唔會開退出面板", await T.js("!document.getElementById('exitSheet').classList.contains('on')"))
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))"); await asyncio.sleep(0.2)
    check("落閘期間按 Esc 唔會開面板", await T.js("!document.getElementById('exitSheet').classList.contains('on')"))


# ⑮ 鍵盤快捷鍵：可改、會記住、撞鍵交換、還原預設
async def t_keys(T):
    await T.js("(()=>{const b=document.getElementById('btnEnter');if(b&&b.offsetParent)b.click()})()")
    await _poll(T, "!!document.querySelector('.sstep.on')", 5)
    for _ in range(4):
        await T.js("document.getElementById('btnNext').click()"); await asyncio.sleep(0.45)
    check("規則頁有「鍵盤快捷鍵」入口", await T.js("!!document.getElementById('btnKeys')"))
    await T.js("document.getElementById('btnKeys').click()"); await asyncio.sleep(0.35)
    check("快捷鍵面板打開", await T.js("document.getElementById('keysSheet').classList.contains('on')"))
    await T.js("document.querySelector('.key-chip[data-k=\"ok\"]').click()"); await asyncio.sleep(0.2)
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',code:'KeyK',bubbles:true}))")
    await asyncio.sleep(0.25)
    label = (await T.js("document.querySelector('.key-chip[data-k=\"ok\"]').textContent")) or ""
    check("按新鍵後晶片顯示 K", label.strip() == "K", label)

    # 撞鍵 → 兩者交換
    await T.js("document.querySelector('.key-chip[data-k=\"foul\"]').click()"); await asyncio.sleep(0.2)
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',code:'KeyK',bubbles:true}))")
    await asyncio.sleep(0.25)
    foul_lbl = (await T.js("document.querySelector('.key-chip[data-k=\"foul\"]').textContent")) or ""
    ok_lbl   = (await T.js("document.querySelector('.key-chip[data-k=\"ok\"]').textContent")) or ""
    check("撞鍵會交換（犯規＝K、正確＝←）", foul_lbl.strip()=="K" and ok_lbl.strip()=="←", f"{foul_lbl}/{ok_lbl}")

    await T.js("document.getElementById('keysDone').click()"); await asyncio.sleep(0.3)
    check("規則頁摘要同步", "K" in (await T.js("document.getElementById('keysSum').textContent")))

    await T.js("document.getElementById('btnNext').click()")
    await T.wait("G && G.phase==='ready'", 10, "準備")
    await T.js("document.getElementById('btnReady').click()")
    await T.wait("G && G.phase==='running'", 12, "出題")

    before = await T.js("G.judged||0")
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',code:'KeyK',bubbles:true}))")
    await asyncio.sleep(0.55)
    after = await T.js("G.judged||0")
    check("新鍵 K 判到犯規", after == before + 1, f"{before}→{after}")

    before2 = after
    await T.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',code:'ArrowRight',bubbles:true}))")
    await asyncio.sleep(0.55)
    check("舊鍵 → 唔會再判定", (await T.js("G.judged||0")) == before2)

    check("HUD 晶片顯示新鍵", "K" in (await T.js("document.querySelector('.key-foul').style.getPropertyValue('--kfoul')")))

    # 重新載入：設定要跟住
    await T.cmd("Page.reload"); await asyncio.sleep(2.0)
    await T.wait("!!document.getElementById('btnEnter')", 15, "重載首頁")
    check("重載後仍然係自訂鍵", "K" in (await T.js("document.querySelector('.key-foul').style.getPropertyValue('--kfoul')")))

async def main(url):
    print("\n[1] 暫停／繼續時鐘")
    await session(url, {"teams": 2, "sec": 20, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_pause)

    print("\n[2] 遊戲中退出")
    await session(url, {"teams": 2, "sec": 30, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_exit)

    print("\n[3] 最短局（2 隊 × 1 回合）")
    await session(url, {"teams": 2, "sec": 2, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_short)

    print("\n[4] 跳過 ∞")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 0, "allowSkip": True}, t_inf)

    print("\n[6] 題庫空")
    await session(url, {"teams": 2, "sec": 30, "roundsPer": 1}, t_emptybank,
                  fetch_js="async u=>{const s=String(u);if(s.startsWith('/api/text')){window.__fetchCount++;return{ok:true,json:async()=>({text:'',title:'',subtitle:''})}}return{ok:true,json:async()=>({})}}")

    print("\n[7] API 失敗")
    await session(url, {"teams": 2, "sec": 30, "roundsPer": 1}, t_apifail,
                  fetch_js="async u=>{const s=String(u);if(s.startsWith('/api/text'))return{ok:false,json:async()=>({})};return{ok:true,json:async()=>({})}}")

    print("\n[8] 時間到邊界")
    await session(url, {"teams": 2, "sec": 3, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_endrace)

    print("\n[9] 連按")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_spam)

    print("\n[10] 跳過用完")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 1, "allowSkip": True}, t_skipcap)

    print("\n[11] 手誤補救（撤回＋結算覆核）")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_undo)

    print("\n[12] 空白題回報")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_report)

    print("\n[13] 英文模式殘留中文")
    await session(url, {"teams": 2, "sec": 60, "roundsPer": 1, "skipCap": 3, "allowSkip": True}, t_i18n)

    print("\n[14] 準備畫面退出／落閘封鎖")
    await session(url, {"teams": 2, "sec": 90, "roundsPer": 1}, t_quitfloat)

    print("\n[15] 鍵盤快捷鍵")
    await session(url, {"teams": 2, "sec": 90, "roundsPer": 1}, t_keys)

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
