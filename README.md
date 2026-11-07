# 百獸台

一個香港派對遊戲：主持用一部 iPad 控場，對錯由人手拍板——冇語音辨識、冇自動判定。

- 主持台：<https://beasttv.vercel.app>
- 題目編輯：<https://beasttv.vercel.app/edit>
- 原始碼：<https://github.com/Kingofpig151251/beaststage>

---

## 玩法

每隊輪流派 **兩位代表**演繹題目，隊友猜；限時 **1 分 30 秒**。
演繹期間不可以講出答案中任何一個字（講了由主持按 **←** 判犯規，扣 1 分）。
每隊出場 **2 回合**（可設 1–5），全部回合打完，總分最高的一隊獲勝。
每答中一題 **+1 分**；每回合最多 **跳 3 條**（可設 1–10，或 **∞ 不限次數**）。

## 主持流程

1. **入口**：百獸台 → 開始
2. **六步設定**：隊伍數量（2–8，預設 4）→ 每隊回合數（1–5，預設 2）→ 隊名（可改動物與隊色）→ 每回合時間（預設 90 秒，另有 30／60／120 或自訂 5–600 秒）→ 規則（可以跳過／每回合可跳幾條／跳過扣 1 分／犯規扣 1 分，犯規預設開）→ 鍵盤快捷鍵（見下）
3. **開場**：上下兩塊藍幕夾合，幕上顯示全部隊伍一字排開，之後分開入場
4. **準備畫面**：第 N 回合（共 N×2 回合）、動物圖示、隊名、全隊分數，按「準備好」繼續
5. **倒數**：獨立過場，3 → 2 → 1 → 開始，數字外圈有每秒遞減的進度環，配三短一長的提示音
6. **一個回合**：出題兼起錶；時間到即落閘
7. **落閘**：重用開場同一對藍幕，由上下夾埋（0.46s）+ 悶響，幕一合即打出「時間到！」
8. **回合結算**：同一塊幕上顯示隊名 + 本回合「答中 N」（有犯規／跳過扣分時才加註）+ 得分（可為負，數字累加），**停住唔會自己走**，按「繼續」或 → 幕才打開，露出下一隊準備畫面。結算卡上的「正確／犯規／跳過」三個數字可以即場加減，改動即時寫回隊分（手誤最後防線）
9. **結果頁**：逐格揭榜——由最後一名開始、由下而上每 0.7s 彈出一行（配一下 tick）；
   揭完第二名後，冠軍位置出現**一張蓋住的卡：整張卡大小、白底、中間一個「?」呼吸、卡身不停震動**
   （震幅 1×→1.7×→2.4×、頻率 0.12s→0.07s，外圈有藍色脈衝環），
   同時密集鼓聲 build-up（0.86× 加速到 1.30×）蓄力；鼓停一下 snare 重擊，
   卡片以 3D **反轉（rotateY 180°，0.62s）** 揭開冠軍卡（隊色光暈、動物圖示擺動、分數 0 數到最終值），
   彩帶由頂一直落下，Celebration BGM 同時起；
   **同分時每個並列第一都各自有一張冠軍卡**（逐張相隔 0.12s 亮起），4 隊以上自動轉緊湊版；
   按 → 或點畫面可即時跳到冠軍，再按 → 返回主頁

出題畫面只有一個大字：冇分數、冇類別、冇剩題數。

## 主持台控件

| 位置 | 控件 | 作用 |
|---|---|---|
| 左上 | chevron | 設定頁 = 上一步；未開始過的遊戲 = 返回設定；已開始 = 退出（先確認） |
| 頂帶中央 | 隊名 chip | 顯示當前隊伍與隊色 |
| 右上 | 計時環 | 剩餘秒數兼進度弧；撳環 = 暫停，再撳繼續 |
| 底部左 | ← 鍵 | 犯規：不計分（可設定扣 1 分），下一題 |
| 底部中 | ↓ 鍵 | 跳過：不計分（可設定扣 1 分），下一題；規則關閉時隱藏 |
| 底部右 | → 鍵 | 正確：+1 分，下一題 |
| 全機 | 體感 | 開啟後可傾斜 iPad 判定：向左犯規、向下跳過、向右正確（預設關閉） |

鍵盤預設：`→` = 正確（準備畫面 = 開始）　`←` = 犯規　`↓` = 跳過　`↑` = 撤回上一個判定　`Esc` = 暫停；四鍵可自訂（見「鍵盤快捷鍵」）。
動畫：**正確 = 文字放大淡出**、**犯規 = 出題卡震動**（扣分時震得更大）、**跳過 = 文字向下墜**。判定鍵本身唔再印方向符號——鍵位可自訂，方向已經無意義。

### 手誤補救

主持按錯是常態，所以有兩層：

- **「↺ 撤回」鍵**（頂欄右邊、計時環左邊；鍵盤亦可按 `↑`）：撤銷本回合最後一次判定——分數、次數、剩餘跳過全部還原，該題放回畫面；每次判定後按鍵會轉為淡藍（提示「仲救得返」），只有一層——新判定即覆蓋、跨回合失效；冇嘢可撤時按落去會提示「沒有可撤回的判定」

三個判定鍵因此維持三粒，撤回歸入頂欄的控制鍵組，與退出、回報、計時環同一 44px 高度、同一圓角語言。

### 鍵盤快捷鍵（可自訂）

設定第 6 步（獨立一頁）就是鍵盤快捷鍵，可以直接改：

| 動作 | 預設 |
|---|---|
| 犯規 | `←` |
| 跳過 | `↓` |
| 正確／準備好／繼續 | `→` |
| 撤回 | `↑` |

- 按一下右邊的鍵晶片，再按鍵盤上的新鍵即成；`Esc` 取消（改完仍留在第 6 步，按「開始遊戲」才開局）
- **撞鍵會自動交換**：把「犯規」改成原本「正確」的鍵，兩個動作的鍵會對調，不會出現兩個動作搶同一個鍵
- **還原預設** 一鍵復原
- 存在 `localStorage["beasttv.keys"]`，**跟這部機**，不跟帳號——換機或借人用不會把別人的鍵位帶過來
- 接受任何鍵：字母、數字、`Space`、`Backspace` 等；修飾鍵（Shift／Ctrl／Alt／Cmd／Tab）與 `Esc`（保留給暫停／關閉面板）不受理
- 三粒判定鍵唔會再顯示方向符號；實際綁定的鍵只出現在「設定第 6 步」同各鍵的 tooltip

### 回報問題（頂欄左邊 `!` 鍵）

遊玩時遇到空白題、卡住、音效異常，按一下就會送出：

- 最近 24 題的出題紀錄（每題的字級、`scrollWidth`／`scrollHeight`、卡片寬高、opacity、`max-width`）
- 當下玩的狀態（隊伍、回合、剩幾秒、暫停與否）
- 裝置資訊（UA、viewport、DPR、是否 standalone）

送到 `POST /api/report`（寫 Neon `reports` 表，保留最近 200 筆）；送不出去就存 `localStorage` 的 `beasttv.reports`（最多 10 筆）。**唔會碰題庫。**
- **結算卡覆核**：時間到之後，結算卡上「正確／犯規／跳過」三個數字附 `−`／`+`，加減即時改隊分與次數（數量不會變負），改完才按「繼續」
所有輸入（鍵盤／觸控／體感）都經同一個 `act()` 動作層入 `judge()`。

**體感操作**（第 4 步開關，預設關閉）：傾斜 iPad 判定，門檻 **18°**、要維持 **150ms** 才成立，
每次觸發後鎖 **600ms** 並以當前角度重新對準中位（回正不會觸發相反動作）。每回合開始會重新對準。
iOS 一定要在用戶手勢內申請 `DeviceOrientationEvent.requestPermission()`，所以只能由開關觸發；
不支援的裝置會提示並保持關閉。觸控與鍵盤永遠可用，體感只是額外輸入。
設定頁：`Enter` = 下一步、`Esc` = 上一步

## 隊伍

8 個動物預設，名稱、圖示、顏色三者綁定且**不可重複使用**：

🐢 烏龜 `#34C759`　🦊 狐狸 `#FF9500`　🐳 鯨魚 `#0071E3`　🐙 章魚 `#AF52DE`
🐝 蜜蜂 `#F5A300`　🦩 火烈鳥 `#FF2D55`　🐬 海豚 `#30B0C7`　🐻 棕熊 `#A2845E`

- 點動物鈕可換動物（連帶換色）；已被其他隊用過的自動變淡並禁用
- 換動物**不會**覆蓋你自己改過的隊名；未改過名的隊才會跟隨動物改名
- 隊色會延伸到準備畫面分數格、遊戲畫面隊名 chip、結果頁名次

## 題目

**題目就是一段純文字，一行一題。** 冇分類、冇組合、冇維護流程。

```
雞蛋仔
菠蘿包
絲襪奶茶
```

- 編輯頁是一個 textarea，改完 **800ms 自動儲存**
- 同一頁可改**標題**（最多 24 字）與**副標題**（最多 36 字），主持台首頁即時套用；留空即用預設「百獸台／派對猜詞主持台」
- 任何人有網址就改得，不用帳號、不用入 repo
- 自動更新：每 15 秒拉一次；切回分頁即時拉；有未存改動時不會覆蓋
- 主持台只讀，出題時抽行洗牌
- 長標題會自動縮字（超過 5 字自動降一級、超過 8 字再降一級），避免壓住動物群像

## API

題庫：

```
GET  /api/text      題目（讀）
PUT  /api/text      整份取代（開放寫入，/edit 用）
```

## 設定頁密碼

`/edit` 開頁要先輸入密碼（存在 Vercel 環境變數 `EDIT_KEY`，不在原始碼裡）。驗證在**伺服器**：

- `PUT /api/text` 必須帶 `x-edit-key: <EDIT_KEY>`，否則回 **401 未授權**
- `GET /api/text?check=1` 只驗密碼（回 `{ok, protected}`），不讀資料庫
- `GET /api/text` 保持開放——主持台要靠它取題目

密碼在該分頁的 sessionStorage 記住，關掉分頁就要再入一次。要改密碼：Vercel → Settings → Environment Variables → `EDIT_KEY`，改完重新部署。
**未設 `EDIT_KEY` 時行為不變（完全開放）**，方便本地開發。

## 開發：smoke test

```bash
python3 -m http.server 8899 --bind 0.0.0.0      # 先開預覽
python3 tests/smoke.py                           # 20 項斷言（首頁→設定→8 隊→一回合→結果頁）
cd tests && python3 edge.py                      # 46 項邊界（暫停、退出、最短局、跳過 ∞、全員同分、撤回、結算覆核）
```

用 headless Chrome + CDP；`fetch` 在頁面載入前打樁，**不會碰 production 題庫**。改動前後各跑一次。

## 安裝成 App（PWA）

`manifest.json` + `sw.js`：加到主畫面後以 standalone 開啟，冇網址列／分頁列——手機橫屏直接多返 60–80px 高度。

- **iPad / iPhone（Safari）**：分享 → 加入主畫面 → 開啟
- **Android（Chrome）**：右上選單 → 安裝應用程式（或等提示）
- **桌面 Chrome / Edge**：網址列右邊的安裝圖示

更新策略：HTML 用 network-first（有網一定攞最新版，離線用快取）；圖片音效用 cache-first；`/api/*` 完全不攔。換素材時把 `sw.js` 的 `CACHE` 版本號 +1。

## 窄屏（手機）

手機不是主力，但**每一頁都唔需要滾動**：

- 隊名步在 ≤460px 自動變兩欄（8 隊 = 4 行）
- 結果頁在窄屏壓縮行高、隱藏統計行；並列冠軍（≥4 隊同分）用緊湊版
- 手機橫向（≤420px 高）：隊名兩欄（圖示鎖正方形）、規則 2×2、結果兩欄
- 準備畫面分數卡改網格：4 隊 4×1、8 隊 4×2，矮屏再壓一級，確保「準備好」永遠在畫面內

已實測 320×568、360×640、390×844、412×915、430×932、740×360、844×390、iPad 直橫，全部 `scrollHeight == clientHeight`。

手機橫屏（瀏覽器工具列佔位後只剩約 300px 高）另有一段極簡壓縮（`max-height:340px`）：標題 18px、數字控件 38px、隊名四欄、規則 2×2，實測 640×300 與 568×320 仍然零滾動。

## 設計

- 明亮系統風格（參考 iOS 排版慣例，與 Apple 無隸屬）：底色 `#F2F2F7`、卡面 `#FFFFFF`、系統藍 `#0071E3`、圓角 12／16／22、髮絲線分隔
- 字階嚴格遞減：頁面標題 30–34 · 卡片 22 · 數值 20 · 內文 17 · 次要 15 · 註腳 13
- 只用 `system-ui`，沒有網絡字體；單檔交付，沒有 build step
- 舞台優先：出題畫面只有一個大字
- 動效：步進 420ms `cubic-bezier(.32,.72,0,1)`、開場幕 460ms、藍幕以 `clip-path` 夾合、倒數每拍 1s、回合結算停留 1.55s
- 落閘、倒數、結算共用同一套藍幕 `clip-path`／位移語言：幕合 → 幕上出字 → 幕開
- 音效走「電視節目」路線，全部係真音源檔（**程式內已無合成音**）：
  **對**＝門鐘叮噹（`sfx/dingdong.mp3`）／**跳過**＝子彈飛過（`sfx/whoosh.mp3`）／**犯規**＝短 snare（`sfx/snare.mp3`）／
  **倒數**＝賽車起步錄音（`sfx/countdown.mp3`）／**最後 10 秒**＝心跳＋滴答（`sfx/hb.mp3`＋`sfx/tick.mp3`）／**時間到**＝球證哨單響（`sfx/whistle.mp3`）／
  **結算卡**＝銅管 fanfare（`sfx/settle.mp3`，2.9s）／**冠軍**＝Celebration 背景音樂（`sfx/champion.mp3`，16.7s 無縫 loop）
- 倒數錄音三個起音正好在 0／1／2 秒、GO 在 3 秒，同畫面每拍 1 秒天生對齊，所以整段照播、不逐拍發聲
- 十個 mp3 合共約 **300KB**，`index.html` 大小不變；第一次觸控時用 `decodeAudioData` 一次過預載，之後播放零延遲
- 冠軍 BGM 以 `loop = true` 無限循環，返回主頁或再開一局即停；音量 0.42，不蓋過現場講話
- 系統開了「減少動態效果」時：動畫時長壓到近 0，倒數改 0.7s 一拍；幕照合、照停，等人按「繼續」；
  結果頁則跳過逐格揭曉，直接顯示完整排名（沒有彩帶）

## 檔案

```
index.html                 主持台（單檔，含 SVG 圖示）
art/team/*.webp            八個隊伍圖示（256×256 透明底，同一批生成圖裁出）
sfx/dingdong.mp3           判定「對」：門鐘叮噹
sfx/whoosh.mp3             判定「跳過」：子彈飛過
sfx/snare.mp3（同時用於犯規判定與冠軍揭曉重擊）
sfx/countdown.mp3          倒數 3／2／1＋開始（真實賽車起步錄音）
sfx/whistle.mp3            時間到：球證哨單響
sfx/settle.mp3             結算卡：銅管 fanfare（2.9s）
sfx/champion.mp3           冠軍揭曉：Celebration loop（16.7s）
sfx/tick.mp3               結果頁每行揭曉的一下短音；亦疊在最後 10 秒的心跳上
sfx/hb3.mp3                最後 10 秒的心跳（真人 61 BPM 錄音，升調 5× ＋ 6dB 對齊喇叭，0.31s）
sfx/tap.mp3                通用按鍵音（介面 chrome 用）
sfx/drums.mp3              冠軍前 build-up 的密集鼓聲（可加速）
sfx/snare.mp3              鼓停、冠軍揭曉的一下重擊
edit.html                  設定頁（標題／副標題／題目，一個 textarea + 自動儲存）
api/_app.py                Vercel 後端（FastAPI + Postgres，只有題庫 GET／PUT）
api/[...path].py / index.py  路由入口
vercel.json                 rewrites、function 設定
tests/mock_sync_server.py  本地 mock 後端（開發用）
samples/hk-icebreaker.json 首次 seed 題庫
```

## 部署

- Vercel 專案 `bigtv` 已連 GitHub：push 上 `main` 自動部署 production
- 環境變數：`DATABASE_URL`（Neon Postgres，Marketplace 自動注入）
- 本地：`python3 tests/mock_sync_server.py` → <http://127.0.0.1:8899>

## 注意／已知取捨

- 冇排行榜：分數只在準備畫面與結果頁出現，不寫入 DB
- 冇帳號系統，題目寫入開放——任何知道網址的人都能改
- 冇快照、冇歷史：一次 `PUT` 就整份覆蓋，舊內容救不回來
- 主持台連不到後端就冇題可玩（冇本機 fallback）
- 猜的人要**背向**屏幕（不是閉眼），一隊 4–8 人最順

## 帳號與題庫（每人一份，互不影響）

**一個帳號 = 一個人 = 一份題庫。** 登入之後，主持台自動載入自己的題庫，其他人完全碰不到。

- 註冊：`/edit` → 「未有帳號？註冊一個」→ **邀請碼** + 用戶名 + 密碼（≥6 字）
  - 邀請碼 = Vercel 環境變數 `CREATE_KEY`；未設定時任何人都可註冊
- 每個新帳號的題庫起頭是 **318 題**（`samples/seed.txt`，分類：香港地標、食物、電影劇集、歌手名人、成語、動作情境、職業、動漫遊戲、日常物品）
- 新帳號即開一份自己的題庫，**用 318 題種子起頭**（即刻玩得到，之後自己改）
- 登入後首頁顯示「已登入：<用戶名>（登出）」；未登入顯示「登入 / 註冊」
- 分享給朋友玩：`/b/<slug>` 是公開唯讀連結（對方不用登入也能玩，但不能改）
- 換裝置：同一個用戶名＋密碼登入即可，題庫一模一樣

安全：密碼 `scrypt(n=2^14, r=8, p=1)` + 每人隨機 salt；session token 30 日，伺服器只存 `sha256(token)`；`PUT /api/text` 只認題庫擁有者（master `EDIT_KEY` 仍可介入維護）。

API：`POST /api/signup`、`POST /api/login`、`POST /api/logout`、`GET /api/me`、`GET/PUT /api/text?b=<slug>`。

### 管理工具（你自己用）

```bash
python3 scripts/bank.py list          # 睇所有題庫（slug、字數、有冇擁有者）
python3 scripts/bank.py text <slug>   # 印出內容
python3 scripts/bank.py rm <slug>     # 刪
```

## 語言（中文／English）

首頁「設定」鍵下方的 `English` 鍵可即時切換全站介面語言（題目本身不翻譯）；設定頁跟隨同一偏好，不再另設語言鍵。

- 偏好存 `localStorage["beasttv.lang"]`，預設中文
- 實作：`EN` 字典 + `translateTree()` 走訪文字節點與 `title`／`aria-label`／`placeholder`；
  動態字串（回合數、分數、統計）逐條雙語
- 新增文案：在 `EN` 字典加一條（key 用中文原文），靜態文字即自動翻譯
- **一律避免換行**：英文比中文長，長句在 `html[lang="en"]` 下 `white-space:nowrap` 並收細一級字階；HUD 與撤回鍵亦已 `nowrap`，≤430px 再收細 padding

## 授權範圍

| 範圍 | 授權 |
|---|---|
| **程式碼**（`index.html`、`edit.html`、`api/`、`tests/`、`sw.js` 等） | **MIT**，全文見 [`LICENSE`](LICENSE) |
| **音效素材**（`sfx/`） | 各自原授權（CC0 / 公有領域 / **CC BY 3.0 / 4.0**） |
| **圖像**（`art/`、icons） | SenseNova 生成，本項目自製 |

> Copyright (c) 2026 **Leung Tung Lam**

MIT 只覆蓋程式碼，**不代表 `sfx/` 變成 MIT**。素材逐項來源、授權與需要的署名見網頁版 **`/credits`**（`credits.html`，唯一維護點）。

兩個需要署名的素材：`hb3.mp3`（Benboncan／Freesound，CC BY 3.0）、`champion.mp3`（Kevin MacLeod《Celebration》，CC BY 4.0）。介面「版權聲明」吐司已列出兩者署名，符合授權要求。

主頁 footer 只留一行：`© 2026 Leung Tung Lam · 版權聲明`（連去 **`/credits`**）。

`/credits` 係獨立文字牆頁（`credits.html`），一次講齊：

- 程式碼 MIT：**英文授權全文**（唔止摘要）
- 音效素材逐項列出來源、授權、以及本項目做過的改動（升調／剪輯／loop）
- 兩個 CC BY 素材標明「必須署名」並連去授權全文
- 圖像來源

唔用吐司／彈出頁的原因：MIT 全文加素材清單接近 2,000 字，吐司放唔落、彈出頁要自己處理捲動同返回；獨立頁可以直連、可被引用、手機單欄自然滾動。

## 版權、致謝與商標

本項目原創部分（程式碼、介面設計、文案）以 **MIT** 授權，`Copyright (c) 2026 Leung Tung Lam`。

**圖像**

八隻動物（首頁散佈插畫與隊伍圖示共用同一套）由 **SenseNova**（`sensenova-u1.5-lite`）生成，
經去背處理後存為 `art/team/*.webp`（256×256 透明底，完整全身）。

**第三方素材**

- **GitHub 圖示**：取自 **Octicons**（MIT）。GitHub 名稱與 Octocat 圖案為 GitHub, Inc. 的商標，
  此處僅用作連結本項目原始碼，不代表任何認可或關聯。
- **字體**：沒有內嵌任何字體檔，只用 `system-ui`；裝置上的系統字體依該裝置授權，不隨本項目轉授。
- **判定音效**：`sfx/dingdong.mp3` 來自 Wikimedia Commons《Doorbell-cheap-dingdong》（Public domain）。
  `sfx/whoosh.mp3` 為本項目自行合成（掃頻噪音），無第三方素材。
- **倒數音效**：`sfx/countdown.mp3` 來自 OpenGameArt《race start countdown》（CC0 1.0）。
- **滴答音效**：`sfx/tick.mp3` 取自 Wikimedia Commons《Clock ticking》（pdsounds.org，public domain），只做裁剪、正規化與淡出。
- **心跳音效**：`sfx/hb3.mp3` 取自 Wikimedia Commons《Human heart beating at 61 bpm》（CC BY 3.0，原錄音 Benboncan／Freesound）。做過裁剪、升調 5×、+6dB：原版 500Hz 以上只有 −44.6dB，iPad 內置喇叭出唔到，調完 −25.3dB 才聽得到。
- **時間到哨子**：`sfx/whistle.mp3` 由 SpliceSound 裁判哨（CC0）剪成單響。
- **結算 fanfare**：`sfx/settle.mp3` 來自 OpenGameArt《Classic fanfare lick》（CC0 1.0）。
- **結果頁鼓聲**：`sfx/drums.mp3` 為 OpenGameArt《Horde War Drums》（William Hector，CC0 1.0）節錄；
  `sfx/snare.mp3` 為 OpenGameArt《An interesting snare drum sound》（CC0 1.0）。
- **冠軍 BGM**：`sfx/champion.mp3` 為 Kevin MacLeod《Celebration》節錄（[incompetech.com](https://incompetech.com)），
  以 **CC BY 4.0** 授權使用，已按授權要求在此署名；16.7 秒（8 小節，114.8 BPM）經交叉淡化做成無縫 loop。
- **依賴**：見 `requirements.txt`（FastAPI、psycopg 等），各自依原授權（MIT / BSD / Apache-2.0）。

**Built with Hermes & OpenCode**

首頁 footer 顯示的 [Hermes](https://hermes-agent.nousresearch.com) 與 [OpenCode](https://opencode.ai/console/go)
圖示屬該兩個專案的品牌標誌，只作致謝與連結用途，不代表任何認可或關聯。

本項目在 [**Hermes**](https://hermes-agent.nousresearch.com)（AI 代理框架）與
[**OpenCode**](https://opencode.ai/console/go)（模型服務）協助下開發，語言模型為 **DeepSeek V4.1 Flash**。
感謝這兩個工具，令一個人也可以做出這樣的東西。

**名稱說明**

**名稱由來**

「百獸」取自隊制的八種動物，「台」同時指電視台與主持台。
「大電視」是香港通用的派對猜詞玩法名稱（源自電視綜藝的同名遊戲環節），本項目只是其中一種主持工具，
**與任何電視節目、電視台或同名手機 App 並無關聯**，亦非任何節目的官方產品。
