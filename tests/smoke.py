#!/usr/bin/env python3
"""百獸台 smoke test：headless Chrome 由首頁玩到結果頁，逐項斷言。

用法：
    python3 tests/smoke.py                 # 用本機預覽
    python3 tests/smoke.py --url <url>     # 指定 URL

前提：preview 已開（NAS: python3 -m http.server 8899 --bind 0.0.0.0）
      fetch 以 CDP 在頁面載入前打樁，唔會碰 production 題庫。
"""
import argparse, asyncio, json, os, shutil, sys, time, urllib.request

import websockets

CHROME = "/opt/data/tools/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell"
DEFAULT_URL = "http://192.168.151.1:8899/index.html"
PORT = 9411

STUB = """
localStorage.setItem("beaststage.cfg.v3", JSON.stringify(
  {teams:8, sec:3, allowSkip:true, skipPenalty:true, foulPenalty:true, roundsPer:1, skipCap:2}));
window.fetch = async (u) => {
  const s = String(u);
  if (s.startsWith("/api/text")) return {ok:true, json:async()=>({text:"甲\\n乙\\n丙\\n丁", title:"", subtitle:""})};
  return {ok:true, json:async()=>({})};
};
window.__err = [];
addEventListener("error", e => window.__err.push(String(e.message)));
"""

class Tab:
    def __init__(self, port):
        self.port, self.id = port, 0

    async def __aenter__(self):
        for _ in range(40):
            try:
                ts = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2).read())
                url = [t for t in ts if t["type"] == "page"][0]["webSocketDebuggerUrl"]
                break
            except Exception:
                await asyncio.sleep(0.25)
        else:
            raise RuntimeError("Chrome 起唔到")
        self.ws = await websockets.connect(url, max_size=32 * 2 ** 20)
        return self

    async def __aexit__(self, *a):
        await self.ws.close()

    async def cmd(self, method, **params):
        self.id += 1
        await self.ws.send(json.dumps({"id": self.id, "method": method, "params": params}))
        while True:
            r = json.loads(await self.ws.recv())
            if r.get("id") == self.id:
                if "error" in r:
                    raise RuntimeError(f"{method}: {r['error']}")
                return r.get("result", {})

    async def js(self, expr):
        r = await self.cmd("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError("JS: " + json.dumps(r["exceptionDetails"])[:400])
        return r["result"].get("value")

    async def wait(self, expr, timeout=8.0, label=""):
        end = time.time() + timeout
        while time.time() < end:
            if await self.js(expr):
                return True
            await asyncio.sleep(0.12)
        raise AssertionError(f"等唔到：{label or expr}")


RESULTS = []

async def _poll(T, expr, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if await T.js(expr): return True
        await asyncio.sleep(0.12)
    return False

def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  ✓ " if cond else "  ✗ ") + name + (f"   [{detail}]" if detail and not cond else ""))


async def main(url, shot):
    proc = await asyncio.create_subprocess_exec(
        CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--autoplay-policy=no-user-gesture-required",
        f"--remote-debugging-port={PORT}", f"--user-data-dir=/tmp/smoke-{os.getpid()}",
        "--window-size=834,1194", "about:blank",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        async with Tab(PORT) as T:
            await T.cmd("Page.enable"); await T.cmd("Runtime.enable")
            await T.cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
            await T.cmd("Page.addScriptToEvaluateOnNewDocument", source=STUB)
            await T.cmd("Page.navigate", url=url)
            await T.wait("!!document.getElementById('btnEnter')", 15, "首頁載入")

            print("\n[1] 首頁")
            check("8 隻動物有渲染", await T.js("document.querySelectorAll('.beast').length") == 8)
            check("動物圖全部載入", await T.js(
                "[...document.querySelectorAll('.beast img')].every(i=>i.complete && i.naturalWidth>0)"))
            check("標題非空", bool(await T.js("document.querySelector('.landing-title').textContent.trim()")))

            print("\n[2] 設定五步")
            for _ in range(3):                      # 入場動畫未完時再按一次，避免 flake
                await T.js("(()=>{const b=document.getElementById('btnEnter');if(b&&b.offsetParent)b.click()})()")
                if await _poll(T, "!!document.querySelector('.sstep.on')", 4): break
            else:
                raise AssertionError("等唔到：第一步")
            overflow = []
            for i in range(5):
                h = await T.js("(()=>{const s=document.querySelector('.sstep.on');return s.scrollHeight-s.clientHeight})()")
                if h > 0: overflow.append((i + 1, h))
                if i < 4:
                    await T.js("document.getElementById('btnNext').click()")
                    await asyncio.sleep(0.45)
            check("五步全部零溢出（834×1194）", not overflow, str(overflow))
            check("到達第 5 步", await T.js("SETUP.i") == 4, f"i={await T.js('SETUP.i')}")

            print("\n[3] 8 隊隊名頁")
            await T.js("goStep(2, 1)")
            await T.wait("document.querySelectorAll('.name-row').length===8", 5, "8 行隊名")
            sq = await T.js("(()=>{const b=document.querySelector('.animal-btn');const r=b.getBoundingClientRect();return Math.abs(r.width-r.height)<1.5})()")
            check("隊名圖示正方形", sq)
            check("8 隊名字有預設值", await T.js("[...document.querySelectorAll('.name-row input')].every(i=>i.value.trim().length>0)"))

            print("\n[4] 準備畫面")
            await T.js("goStep(4, 1)"); await asyncio.sleep(0.3)
            await T.js("document.getElementById('btnNext').click()")   # 真正開局
            await T.wait("G && G.phase==='ready'", 8, "準備畫面")
            check("準備畫面 8 張分數卡", await T.js("document.querySelectorAll('#rdScores .score-tile').length") == 8)
            check("「準備好」在畫面內", await T.js(
                "(()=>{const b=document.getElementById('btnReady').getBoundingClientRect();return b.bottom<=innerHeight+1 && b.top>=0})()"))
            check("回合顯示 1 / 8", (await T.js("document.querySelector('#rdRound, .readyRound')?.textContent || ''")).find("1") >= 0)

            print("\n[5] 一回合判定")
            await T.js("document.getElementById('btnReady').click()")
            await T.wait("G && G.phase==='running'", 6, "倒數完成")
            for _ in range(3):
                await T.js("act('ok')"); await asyncio.sleep(0.28)
            await T.js("act('skip')"); await asyncio.sleep(0.28)
            await T.js("act('foul')"); await asyncio.sleep(0.35)
            t = await T.js("(()=>{const t=curTeam();return {ok:t.ok,skip:t.skip,foul:t.foul,score:t.score}})()")
            check("答中 3 次扣回跳過＋犯規 = 1 分", t["ok"] == 3 and t["score"] == 1, str(t))
            check("跳過／犯規有計數", t["skip"] == 1 and t["foul"] == 1, str(t))
            check("大字有題目", bool(await T.js("document.querySelector('#stage').textContent.trim()")))

            print("\n[6] 時間到 → 落閘 → 結算卡")
            await T.wait("G && G.phase==='interstitial'", 12, "回合結束")
            check("落閘有開", await T.js("document.getElementById('gate').classList.contains('on')"))
            await T.wait("document.getElementById('teCard')?.classList.contains('on') || document.querySelector('#teName').textContent.trim().length>0", 8, "結算卡")
            check("結算卡有隊名", bool(await T.js("document.querySelector('#teName').textContent.trim()")))
            sc_txt = (await T.js("document.querySelector('#teScore').textContent")).strip()
            check("結算卡分數 = 1", sc_txt.replace("+", "").replace("分", "").strip() == "1", f"實際 {sc_txt!r}")

            print("\n[7] 繼續 → 下一隊 → 全部打完")
            await T.js("document.getElementById('teNext').click()")
            await _poll(T, "G && G.turn >= 1", 6)          # 輪詢而非固定 sleep，避免過場時間浮動造成 flake
            check("回合索引已前進", (await T.js("G ? G.turn : -1")) >= 1, f"turn={await T.js('G ? G.turn : -1')}")
            # 逐回合驅動：ready→countdown→running→interstitial→下一隊
            for _ in range(80):
                ph = await T.js("G ? G.phase : 'none'")
                if ph == "done": break
                if ph in ("ready", "countdown"):
                    await T.js("(()=>{const b=document.getElementById('btnReady');if(b&&b.offsetParent)b.click()})()")
                    await asyncio.sleep(1.1)
                elif ph == "running":
                    await asyncio.sleep(1.2)
                elif ph == "interstitial":
                    await asyncio.sleep(1.4)
                    await T.js("(()=>{const b=document.getElementById('teNext');if(b&&b.offsetParent)b.click()})()")
                    await asyncio.sleep(0.9)
                else:
                    await asyncio.sleep(0.4)
            await T.wait("G && G.phase==='done'", 60, "結果頁")
            check("結果頁有排名", await T.js("document.querySelectorAll('#rankList .rk').length") >= 4)
            check("有冠軍卡", await T.js("!!document.querySelector('#rankList .rk.is-champ')"))
            check("結果頁無 JS 例外", (await T.js("window.__err.length")) == 0,
                  str(await T.js("window.__err")))
            # 回歸：冠軍頁「返回主頁」（曾因殘留 sessionStop() 拋 ReferenceError）
            await T.js("document.getElementById('btnBackHome').click()")
            await asyncio.sleep(0.8)
            check("返回主頁有效", (await T.js("document.body.dataset.view")) == "home",
                  str(await T.js("document.body.dataset.view")))
            check("返回主頁已清空舊局", (await T.js("G === null")) is True, str(await T.js("G && G.phase")))
            check("返回主頁無 JS 例外", (await T.js("window.__err.length")) == 0,
                  str(await T.js("window.__err")))

            if shot:
                await T.cmd("Page.captureScreenshot")
                print(f"\n（結果頁截圖存到 {shot}）")
    finally:
        proc.kill()
        shutil.rmtree(f"/tmp/smoke-{os.getpid()}", ignore_errors=True)

    ok = all(r[1] for r in RESULTS)
    print(f"\n{'PASS' if ok else 'FAIL'} — {sum(r[1] for r in RESULTS)}/{len(RESULTS)} 項通過")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--shot", default="")
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.url, a.shot)))
