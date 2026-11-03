# 大電視 · 破冰主持台

一個遊戲：**大電視**。主持一部 iPad 控場，對錯由人手拍板——冇語音辨識、冇自動判定。

玩法：一隊派一人背向屏幕，屏幕出一個詞，全隊用講嘢／做動作提示（唔准講出題目上面任何一隻字），主持按「對／跳過」，限時內猜得多就贏。

- 主持台：`https://bigtv.vercel.app`
- 題庫：只存雲端，所有機共用同一份

---

## 一、主持流程

1. 主頁揀隊數（2 / 4 / 6 / 8）、打隊名、設每回合秒數
2. 撳「開始遊戲」
3. 每隊出場前有**準備畫面**：大字隊名＋全隊分數＋「派一個人背向屏幕」
4. 撳「開始」→ 3、2、1 倒數（每格 1.15 秒）→ 出題兼起錶
5. 時間到自動停，跳去下一隊嘅準備畫面

出題畫面只有一個大字，冇分數、冇類別名、冇剩題數。

## 二、主持台控件

| 位置 | 控件 | 作用 |
|---|---|---|
| 左上 | 退出 icon | 確認後結束遊戲，返主頁 |
| 右上 | 計時環 | 顯示剩餘秒數兼進度弧；**撳環 = 暫停**，再撳繼續 |
| 底部 | 跳過 | 唔計分，下一題 |
| 底部 | 對 | +1 分，下一題 |

鍵盤：`Space`／`Enter` = 對（準備畫面時 = 開始）　`S`／`↓` = 跳過　`Esc`／`P` = 暫停

## 三、題目（`/edit`）

**題目就係一段純文字，一行一題。** 冇分類、冇組合、冇維護流程。

```
雞蛋仔
菠蘿包
絲襪奶茶
```

- 編輯頁：一個 textarea，改完 **800ms 自動儲存**
- 任何人有網址就改得，唔使帳號、唔使 repo
- 自動更新：每 15 秒拉一次；切返分頁即刻拉；有未存改動時唔會覆蓋你
- 後端每次覆寫前留 3 份快照（`meta` 表 `snap1`–`snap3`）
- 主持台只讀，出題就係由呢段文字抽行、洗牌

## 四、API

```
GET    /api/ping
GET    /api/text                    題目（讀）
PUT    /api/text                    整份取代（開放寫入，/edit 用）
```

## 五、題庫格式

```json
{ "name": "我嘅題庫",
  "decks": [ { "id": "food", "name": "港式小食", "items": ["雞蛋仔", "菠蘿包"] } ],
  "sets":  [ { "id": "s1", "name": "第一回合", "items": ["food:0", "food:3"] } ] }
```

## 六、設計

- 視覺語言：Brutalism（2px 邊、圓角 0、單一硬陰影、4 級字階）
- 色角色：ember 橙 = 當前動作；acid 綠 = 時間／成功／連線；其餘灰階
- 規範：`docs/design-spec.md`；審查：`docs/design-audit.md`；功能取捨：`docs/feature-audit.md`
- 量度腳本：`tests/audit.js`（觸控目標、字級、圓角、邊框、對比）

## 七、部署

- GitHub：`Kingofpig151251/bigtv`（private）
- Vercel 專案 `bigtv` 已連 GitHub：**push 上 main 自動部署 production**
- 環境變數：`DATABASE_URL`（Neon Postgres，Marketplace 自動注入）
- 本地開發：`vercel dev`

## 八、檔案

```
index.html                 主持台（單檔）
edit.html                  題目編輯（一個 textarea，自動儲存）
api/_app.py                Vercel 後端（FastAPI + Postgres）
api/[...path].py           catch-all 入口
api/index.py               深路徑入口
vercel.json / requirements.txt
docs/                      設計規範、設計審查、功能審查、版面方案
tests/audit.js             DOM 量度腳本
tests/mock_sync_server.py  本地 mock 後端（開發用）
samples/hk-icebreaker.json 新 DB 首次 seed 題庫（6 類 62 題）
```

## 九、注意

- 冇排行榜：分數只在準備畫面同結果頁出現，唔寫入 DB
- 冇帳號系統；題庫寫入開放
- 主持台連唔到後端就冇題可玩（冇本機 fallback）
- 經典擺位：猜嗰個要**背向**屏幕（唔係閉眼），一隊 4–8 人最順

## 十、授權

本項目以 **MIT License** 開源，全文見 [`LICENSE`](LICENSE)。

> Copyright (c) 2026 **Leung Tung Lam**

轉載、修改、商用皆可，唯一要求是保留上面的版權聲明與授權條文。
介面左下／底部顯示嘅 `© 2026 Leung Tung Lam · MIT License` 屬作者署名，請勿移除。

## 十一、第三方素材與商標

- **Twemoji**（動物圖示 🐢🦊🐳🐙🐝🦩🐬🐻）：**CC-BY 4.0**，<https://github.com/jdecked/twemoji>
  —— 以內嵌 SVG 放在 `index.html` 的 `ICONS`，圖形未經修改。
- **字體**：冇內嵌任何字體檔，只用 `system-ui`；Apple 裝置上解析為 SF Pro（Apple Inc. 系統字體，不隨本項目轉授）。
- **依賴**：見 `requirements.txt`，各自依原授權（MIT / BSD / Apache-2.0）。

完整版權與第三方清單見 [`NOTICE.md`](NOTICE.md)。

## 十二、AI 使用聲明

本項目在開發過程中使用 AI 編碼助理協助實作。**產品方向、設計決定、內容定稿、測試與發佈
均由作者 Leung Tung Lam 負責**；AI 不具備決定權，亦非共同作者。

| 層級 | 工具 |
|---|---|
| 代理框架 | Hermes Agent（Nous Research） |
| 模型服務 | OpenCode（Go 方案） |
| 語言模型 | DeepSeek V4.1 Flash |

完整聲明（參與範圍、審核流程、第三方素材、使用者提示、英文摘要）見
[`AI-DISCLOSURE.md`](AI-DISCLOSURE.md)。

## 十三、參與方式

本項目由作者 **Leung Tung Lam** 獨立開發，**不接受外部 Pull Request，也不打算與他人共同開發**。
程式碼以 MIT 授權公開，你可以自由 fork、修改、自行發佈（請保留授權與署名）。

- **Bug 回報與功能建議**：歡迎開 GitHub Issue，但作者不保證回應時間或採納。
- **安全問題**：請依 [`SECURITY.md`](SECURITY.md) 私下回報，不要開公開 issue。
- **自行維護的分支**：與本項目無隸屬關係，作者不提供支援。
