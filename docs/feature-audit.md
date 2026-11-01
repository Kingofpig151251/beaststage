# 大電視 · 功能審查（2026-10-31）

> 判準：派對現場，主持坐定、iPad 一塊屏、4+ 隊、人手判定。
> 一個功能留唔留，睇三樣：**現場會唔會用**、**有冇第二個入口做同一件事**、**維護成本**。

---

## A · 多餘（建議直接刪）

| # | 功能 | 證據 | 影響 |
|---|---|---|---|
| A1 | **8 個冇人 call 嘅 API**：`POST /api/login`、`GET /api/sessions`、`DELETE /api/sessions/{sid}`、`POST /api/decks`、`PATCH /api/decks/{did}`、`DELETE /api/decks/{did}`、`POST /api/decks/{did}/items`、`PATCH /api/items/{iid}`、`DELETE /api/items/{iid}`、`POST /api/reset` | 前端只有 4 個 fetch：`GET/PUT /api/bank`、`POST /api/sessions`、`GET /api/leaderboard` | `_app.py` 448 行中約 **180 行**係死碼；連帶 token 機制（`make_token`/`token_ok`/`need_token`，27 行）亦只剩死碼用 |
| A2 | **16 行空註解區塊** | `grep -c "<!-- =========="` = 16，全部下面冇內容（排行榜／結果／題庫重複 4 次） | 純噪音，改 markup 時容易誤插 |
| A3 | **全螢幕掣** | `if(!document.documentElement.requestFullscreen)` → iPad Safari 冇呢個 API，掣永遠 `display:none` | 目標裝置上等於唔存在；桌面才有用 |
| A4 | **第二套後端** `server.py`（489 行）＋ `tests/test_api_local.py`（130 行）＋ `samples/hk-icebreaker.json`（102 行） | 前端只打 `/api/*`；Vercel 版已覆蓋全部功能 | 同一件事兩份實作，改一邊另一邊即刻過時（seed 已經係咁） |
| A5 | **隊伍數有兩套控件**：`−/＋` stepper ＋ `2/4/6/8` presets | 兩個都寫 `cfg.teams`；stepper 容許 1 隊（呢個遊戲 1 隊冇意義），presets 最小 2 | 一屏兩個控件講同一件事；派對現場 presets 一撳到位，stepper 係多餘 |
| A6 | **「畫面動效」checkbox ＋ 兩行說明** | 主頁 `#vfxChk`，下面仲有一句「動效係答對閃光、跳過震動同倒數彈跳」 | 派對現場冇人會入去關動效；同 BGM 一樣屬設定噪音，而且食咗兩行版面 |

**A 合計**：約 750 行可刪（`_app.py` 180 ＋ `server.py` 489 ＋ tests 130），主頁少一組控件。

---

## B · 邊界（要你決定）

| # | 功能 | 問題 |
|---|---|---|
| B1 | **排行榜「累計」** | 隊名跨場重複（永遠係「A 隊」），累計分數會把唔同場合、唔同人嘅分加埋一齊。數字會存在，但意思模糊 |
| B2 | **排行榜「最近場次」** | 同結果頁睇嘅嘢一樣，只係多一個入口 |
| B3 | **結果頁三個掣**：再玩一次／排行榜／返主頁 | 「排行榜」喺主頁已經有入口 |
| B4 | **題目組合（sets）** | 你之前要求過；但目前 `sets` 係空，主頁永遠只顯示「全部」，等於未用過 |
| B5 | **組合頁「搜尋題目」** | 62 題時多餘；去到 500 題就有用 |
| B6 | **題庫狀態顯示兩處** | 主頁 pill「題庫：已連線」＋ 題庫頁「已同步」點；另外 `#srcPill` 初始字串仍寫「題庫來源：本機」（錯，開機即被 JS 覆蓋） |

---

## C · 保留（核心）

- 主持台：退出 · 計時環（兼暫停）· 跳過 · 對
- 準備畫面：隊名 · 全隊分數 · 開始
- 題庫：一行一題 textarea、`# 類別` 開類別、自動儲存、3 份快照
- 結果：冠軍塊 ＋ 其餘名次
- 排行榜：`POST /api/sessions` 寫入 ＋ `players` 聚合
- toast、鍵盤快捷（Space 開始、Esc 暫停）

---

## 建議

1. **A 全刪**（A1–A6），主頁只留 presets，唔留 stepper
2. B1 若保留排行榜，建議**隊名改成可記住嘅名**（例如「陳小明隊」）才有累計意義；否則累計只能睇「玩咗幾多場」
3. B4 題目組合：如果派對唔會分組出題，直接刪走（少一個 tab、少一個 picker）
4. B6 主頁 pill 刪走，狀態只留題庫頁一個地方
