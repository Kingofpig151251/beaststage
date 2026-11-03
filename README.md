# 大電視

一個香港派對遊戲：主持用一部 iPad 控場，對錯由人手拍板——冇語音辨識、冇自動判定。

- 主持台：<https://bigtv.vercel.app>
- 題目編輯：<https://bigtv.vercel.app/edit>
- 原始碼：<https://github.com/Kingofpig151251/bigtv>

---

## 玩法

一隊派一人**背向屏幕**，屏幕出一個詞，全隊用說話／動作提示（不可以講出題目上任何一隻字），
主持按 **→** 判對、按 **←** 判跳過，限時內猜得多就贏。

## 主持流程

1. **入口**：大電視 → 開始
2. **三步設定**：隊伍數量（2–8）→ 隊名（可改動物與隊色）→ 每回合時間（30／60／90／120 或自訂 5–600 秒）
3. **開場**：上下兩塊藍幕夾合，幕上顯示全部隊伍一字排開，之後分開入場
4. **準備畫面**：第 N 隊、動物圖示、隊名、全隊分數，按「準備好」繼續
5. **倒數**：獨立過場，3 → 2 → 1 → 開始，數字外圈有每秒遞減的進度環，配三短一長的提示音
6. **一個回合**：出題兼起錶；時間到即落閘
7. **落閘**：重用開場同一對藍幕，由上下夾埋（0.46s）+ 悶響，幕一合即打出「時間到！」
8. **回合結算**：同一塊幕上顯示隊名 + 本回合「對 N · 跳過 M」+ 得分（數字累加），**停住唔會自己走**，按「繼續」或 → 幕才打開，露出下一隊準備畫面
9. **結果頁**：冠軍卡 + 其餘名次

出題畫面只有一個大字：冇分數、冇類別、冇剩題數。

## 主持台控件

| 位置 | 控件 | 作用 |
|---|---|---|
| 左上 | chevron | 設定頁 = 上一步；未開始過的遊戲 = 返回設定；已開始 = 退出（先確認） |
| 頂帶中央 | 隊名 chip | 顯示當前隊伍與隊色 |
| 右上 | 計時環 | 剩餘秒數兼進度弧；撳環 = 暫停，再撳繼續 |
| 底部左 | ← 鍵 | 跳過：不計分，下一題 |
| 底部右 | → 鍵 | 對：+1 分，下一題 |

判定只有方向鍵：`→` = 對（準備畫面 = 開始）　`←` = 跳過　`Esc` = 暫停
設定頁：`Enter` = 下一步、`Esc` = 上一步

## 隊伍

8 個動物預設，名稱、圖示、顏色三者綁定且**不可重複使用**：

🐢 烏龜 `#34C759`　🦊 狐狸 `#FF9500`　🐳 鯨魚 `#0071E3`　🐙 章魚 `#AF52DE`
🐝 蜜蜂 `#F5A300`　🦩 火烈鳥 `#FF2D55`　🐬 海豚 `#30B0C7`　🐻 棕熊 `#A2845E`

- 點動物鈕可換動物（連帶換色）；已被其他隊用過的會標示「第 N 隊已選」並禁用
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
- 任何人有網址就改得，不用帳號、不用入 repo
- 自動更新：每 15 秒拉一次；切回分頁即時拉；有未存改動時不會覆蓋
- 主持台只讀，出題時抽行洗牌

## API

```
GET  /api/text      題目（讀）
PUT  /api/text      整份取代（開放寫入，/edit 用）
```

## 設計

- 明亮系統風格（參考 iOS 排版慣例，與 Apple 無隸屬）：底色 `#F2F2F7`、卡面 `#FFFFFF`、系統藍 `#0071E3`、圓角 12／16／22、髮絲線分隔
- 字階嚴格遞減：頁面標題 30–34 · 卡片 22 · 數值 20 · 內文 17 · 次要 15 · 註腳 13
- 只用 `system-ui`，沒有網絡字體；單檔交付，沒有 build step
- 舞台優先：出題畫面只有一個大字
- 動效：步進 420ms `cubic-bezier(.32,.72,0,1)`、開場幕 460ms、藍幕以 `clip-path` 夾合、倒數每拍 1s、回合結算停留 1.55s
- 落閘、倒數、結算共用同一套藍幕 `clip-path`／位移語言：幕合 → 幕上出字 → 幕開
- 音效走「電視節目」路線，全部係真音源檔（**程式內已無合成音**）：
  **對**＝門鐘叮噹（`sfx/dingdong.mp3`）／**跳過**＝子彈飛過（`sfx/whoosh.mp3`）／
  **倒數**＝賽車起步錄音（`sfx/countdown.mp3`）／**時間到**＝球證哨三吹（`sfx/whistle.mp3`）／
  **結算卡**＝銅管「噠」（`sfx/settle.mp3`）／**冠軍**＝色士風 fanfare（`sfx/champion.mp3`）
- 倒數錄音三個起音正好在 0／1／2 秒、GO 在 3 秒，同畫面每拍 1 秒天生對齊，所以整段照播、不逐拍發聲
- 六個 mp3 合共約 **110KB**，`index.html` 大小不變；第一次觸控時用 `decodeAudioData` 一次過預載，之後播放零延遲
- 系統開了「減少動態效果」時：動畫時長壓到近 0，倒數改 0.7s 一拍；幕照合、照停，等人按「繼續」

## 檔案

```
index.html                 主持台（單檔，含 SVG 圖示）
sfx/dingdong.mp3           判定「對」：門鐘叮噹
sfx/whoosh.mp3             判定「跳過」：子彈飛過
sfx/countdown.mp3          倒數 3／2／1＋開始（真實賽車起步錄音）
sfx/whistle.mp3            時間到：球證哨三吹
sfx/settle.mp3             結算卡：銅管「噠」
sfx/champion.mp3           冠軍揭曉：色士風 fanfare
edit.html                  題目編輯（一個 textarea + 自動儲存）
api/_app.py                Vercel 後端（FastAPI + Postgres，2 個路由）
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

## 授權

**MIT License**，全文見 [`LICENSE`](LICENSE)。

> Copyright (c) 2026 **Leung Tung Lam**

可自由使用、修改、商用，唯一要求是保留版權聲明與授權條文；介面上的
`© 2026 Leung Tung Lam · MIT License` 屬作者署名，請勿移除。

## 版權、致謝與商標

本項目原創部分（程式碼、介面設計、文案）以 **MIT** 授權，`Copyright (c) 2026 Leung Tung Lam`。

**第三方素材**

- **動物圖示**：Emoji artwork provided by **Twemoji**, licensed under **CC BY 4.0**
  （<https://github.com/jdecked/twemoji>）。以內嵌 SVG 使用，圖形未經修改。
- **GitHub 圖示**：取自 **Octicons**（MIT）。GitHub 名稱與 Octocat 圖案為 GitHub, Inc. 的商標，
  此處僅用作連結本項目原始碼，不代表任何認可或關聯。
- **字體**：沒有內嵌任何字體檔，只用 `system-ui`；裝置上的系統字體依該裝置授權，不隨本項目轉授。
- **判定音效**：`sfx/dingdong.mp3` 來自 Wikimedia Commons《Doorbell-cheap-dingdong》（Public domain）。
  `sfx/whoosh.mp3` 為本項目自行合成（掃頻噪音），無第三方素材。
- **倒數音效**：`sfx/countdown.mp3` 來自 OpenGameArt《race start countdown》（CC0 1.0）。
- **時間到哨子**：`sfx/whistle.mp3` 由 SpliceSound 裁判哨（CC0）剪成三吹。
- **結算與冠軍**：`sfx/settle.mp3`、`sfx/champion.mp3` 來自 Kenney《Music Jingles》（CC0 1.0）。
- **依賴**：見 `requirements.txt`（FastAPI、psycopg 等），各自依原授權（MIT / BSD / Apache-2.0）。

**Built with Hermes & OpenCode**

首頁 footer 顯示的 [Hermes](https://hermes-agent.nousresearch.com) 與 [OpenCode](https://opencode.ai/console/go)
圖示屬該兩個專案的品牌標誌，只作致謝與連結用途，不代表任何認可或關聯。

本項目在 [**Hermes**](https://hermes-agent.nousresearch.com)（AI 代理框架）與
[**OpenCode**](https://opencode.ai/console/go)（模型服務）協助下開發，語言模型為 **DeepSeek V4.1 Flash**。
感謝這兩個工具，令一個人也可以做出這樣的東西。

**名稱說明**

「大電視」是香港通用的派對猜詞遊戲名稱（源自電視綜藝的同名遊戲環節）。
本項目是獨立開發的主持工具，**與任何電視節目、電視台或同名手機 App 並無關聯**，
亦非任何節目的官方產品。
