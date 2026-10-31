# 大電視 · 破冰主持台

一個遊戲：**大電視**。主持一部機控場，對錯由人手拍板——冇語音辨識、冇自動判定。

玩法：一隊派一人背向屏幕，屏幕出題，全隊用講嘢／做動作提示（唔准講出題目上面任何一隻字），主持按「對／跳過」，限時內猜得多就贏。

兩種用法：

| 模式 | 點用 | 題庫 | 排行榜 |
|---|---|---|---|
| **本機**（單檔） | 雙擊 `index.html` | 存喺瀏覽器 | 冇 |
| **自架**（建議） | `python3 server.py` 或 Docker | 存 SQLite，多部機共用 | 有，累計＋場次紀錄 |

---

## 一、快速開始

### 本機（唔使 server）
雙擊 `index.html`。離線、零依賴、資料留喺 localStorage。
缺點：換機要自己匯出／匯入 JSON；冇歷史排行榜。

### 自架（有後台 + 排行榜）
```bash
BIGTV_PIN=2468 python3 server.py
```
- 主持台：`http://localhost:8080`
- 後台：`http://localhost:8080/admin`（密碼 = `BIGTV_PIN`）

或者 Docker：
```bash
docker compose up -d          # 預設 8080，資料喺 ./data
```

只用 Python 標準庫 + SQLite，**冇 pip install、冇 database server**。
首次啟動自動載入 `samples/hk-icebreaker.json` 做預設題庫。

環境變數：`BIGTV_PORT`（8080）、`BIGTV_PIN`（2468，正式一定要改）、`BIGTV_DB`（`./data/bigtv.db`）

---

## 二、介面

介面由 Hallmark（Together AI 嘅設計 skill）做過一次 redesign：深紫黑 CRT 底、ember 橙做主持動作、acid 綠做答方、按鍵有硬陰影（press physics）；玩法同接線全部唔變。

- 主頁：設定分兩欄，開始鍵固定喺底欄
- 遊戲：題目佔大版面，分數板同判定鍵喺下面，投影距離都睇得清
- 準備畫面：ember 卡，3、2、1 倒數每格 1.15 秒
- 字型用系統字（唔載 webfont），因為要單檔離線用得

**iPad 適配**：已按 iPad 實際 CSS 尺寸調過（mini 744×1133、Air 820×1180、Pro 11" 834×1194、Pro 13" 1024×1366，橫度對調）

- 1024 闊以上兩欄設定，iPad 直度單欄；所有 iPad 尺寸遊戲畫面唔使捲
- 觸控目標：判定鍵 69–87px、加減掣 44×44、分類 chip 46px 高、輸入框 16px 字（iOS 唔會自動放大）
- 支援 `viewport-fit=cover` + `safe-area-inset`，圓角／Home Indicator 唔會蓋住內容
- hover 效果只在有滑鼠嘅裝置生效，iPad 唔會「黏住」上一個 hover
- 加咗 `apple-mobile-web-app-capable`：iPad Safari「加到主畫面」後以全屏 App 方式開，冇瀏覽器工具列（推薦主持用）
- `color-mix` / `dvh` 有 fallback，舊 iPadOS 唔會爛色或爆高度

## 三、設定

- **組別／玩家**：1–8 個，可以打玩家名（唔一定要分隊）
- **每回合時限**：預設 60 秒（0 = 不限時，主持自己按「結束本回合」）
- **總回合數**：每隊輪流一次 = 1 回合
- **題庫**：多選類別，即場組合；題目用晒會自動重新洗牌

計分：對 +1、跳過 0。判定只有兩個掣：**對**同**跳過**。

**回合流程**：每隊出場前有個「準備畫面」（大字隊名＋提示），撳「開始」後 **3、2、1 倒數（每格 1.15 秒）** 才出題兼計時；時間到或者撳「結束本回合」之後會停返喺下一隊嘅準備畫面，唔會即刻幫佢開錶。

**兩個全域開關**：
- **背景音樂**：程序化四和弦（WebAudio，冇音檔），同時包住提示音同倒數聲；關咗就全靜音
- **畫面動效**：答對綠色閃光＋「+1」、跳過震動、倒數彈跳、最後 5 秒鐘脈動；關咗純靜態

兩個設定都存喺瀏覽器，跟機跟人。

## 三、主持快捷鍵

`Space`／`Enter` = 對　`S` = 跳過　`Z` = 撤銷　`Esc`／`P` = 暫停

配平板或者 notebook 用最順手；「全螢幕」可以將部機變純題目屏。

## 四、後台（`/admin`）

PIN 登入後：

- **題庫**：左邊類別（新增／改名／刪除），右邊逐題改，改完自動儲存
- **批量新增**：每行一題，重覆自動跳過
- **匯入 JSON**：同名類別合併，唔會覆蓋
- **匯出 JSON**：帶去另一部機或者做備份
- **排行榜**：累計榜（總分／場次／最佳／答對數）、最近場次、逐場刪除、清空成績

主持台完場會自動上報成績（連到後端時）。**玩家名就係身份**，同名累計埋一齊。

## 五、API

```
GET    /api/ping
GET    /api/bank                    題庫（主持台同後台共用）
PUT    /api/bank                    整份取代（要登入）
POST   /api/login {pin} → {token}    token 放 X-Admin-Token header
GET    /api/leaderboard?limit=10    累計榜 + 最近場次
POST   /api/sessions                完場上報（免登入）
GET    /api/sessions?limit=20
DELETE /api/sessions/{id}           要登入
POST   /api/decks {name}            要登入
PATCH  /api/decks/{id} {name}
DELETE /api/decks/{id}
POST   /api/decks/{id}/items {items}  批量加題（自動去重）
PATCH  /api/items/{id} {t}
DELETE /api/items/{id}
POST   /api/reset {what:"sessions"|"bank"}
```

## 六、題庫格式

```json
{ "name": "我嘅題庫",
  "decks": [
    { "id": "food", "name": "港式小食", "items": ["雞蛋仔", "菠蘿包"] }
  ] }
```
`items` 亦接受 `{"t":"雞蛋仔"}` 格式；舊嘅 `ban` 欄位會被忽略（呢個 app 只做大電視，唔使禁字）。

## 七、雲端部署（Vercel）

雲端版用 `api/`（FastAPI + Postgres），因為 serverless 冇持久磁碟，SQLite 用唔到。

1. GitHub repo：`Kingofpig151251/bigtv`（private）
2. Vercel 專案 `bigtv` 已連 GitHub：**push 上 main 就自動部署去 production**
3. 環境變數（Vercel → Settings → Environment Variables）
   - `DATABASE_URL`：Neon Postgres（由 Vercel Marketplace 的 Neon integration 自動注入）
   - `BIGTV_PIN`：後台密碼
   - `BIGTV_SECRET`：簽登入 token 用（serverless 冇共享記憶體，改用 HMAC 簽名）
4. 本地開發：`vercel dev`（會用 `.env.local`），或者照用 `python3 server.py`

兩套後端共用同一份前端同同一套 `/api/*` 介面，揀邊個跑睇部署環境。

## 八、檔案

```
index.html                 主持台（單檔，可獨立用）
admin.html                 後台
server.py                  自架版後端（Python 標準庫 + SQLite）
api/_app.py                Vercel 版後端（FastAPI + Postgres）
api/[...path].py           Vercel catch-all 入口
vercel.json / requirements.txt
tests/test_api_local.py    API smoke test（sqlite shim）
Dockerfile / docker-compose.yml
samples/hk-icebreaker.json 內建香港題庫（6 類共 62 題）
data/bigtv.db              SQLite（首次啟動自動建立）
```

## 八、注意

- 排行榜身份係**名字**：兩個唔同人打同一個名會累計埋。想分清楚就各自改花名。
- 備份就備 `data/`（SQLite 單檔），其餘嘢無狀態。
- 冇帳號系統，只有一條 PIN；只適合屋企／內網，唔好直接掛上公網。
- 主持台連唔到後端會自動 fallback 本機模式，唔會玩唔到。
- 後台編輯即時寫入 DB，冇 undo；誤刪就靠匯出嘅 JSON 備份。
- 經典擺位：猜嗰個要**背向**屏幕（唔係閉眼），一隊 4–8 人最順。
