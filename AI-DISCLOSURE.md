# AI 使用聲明 / AI Usage Disclosure

版本 1.0 · 2026-11-03 · Leung Tung Lam

---

## 一、摘要

本項目（大電視 / Big TV，下稱「本軟件」）在開發過程中使用了 **AI 編碼助理**協助撰寫與修改程式碼、樣式及文案。

所有**產品方向、設計決定、內容定稿、測試與發佈**均由作者本人作出並承擔責任。
AI 只作為實作工具，不具備決定權，亦不構成共同作者。

## 二、使用的工具與模型

| 層級 | 工具 | 說明 |
|---|---|---|
| 代理框架 | **Hermes Agent**（Nous Research） | 執行開發任務的 AI 代理環境，負責讀寫檔案、跑測試、部署 |
| 模型服務 | **OpenCode**（Go 方案） | 提供模型存取與額度 |
| 語言模型 | **DeepSeek V4.1 Flash** | 實際生成與修改程式碼／文案的模型 |

除上述工具外，本項目沒有使用其他 AI 服務生成程式碼、圖像或資料集。

## 三、AI 參與的範圍

**由 AI 協助：**

- HTML／CSS／JavaScript 的實作與重構
- 版面、動畫與互動邏輯的初稿
- API 與資料存取層的初稿
- 介面文案的草稿（最終用語由作者定稿）
- 重複性工作：lint 修正、量測腳本、部署驗證

**由作者負責：**

- 產品定位、玩法與流程設計
- 視覺取向與設計取捨（顏色、字階、動效節奏）
- 題目內容與香港用語的定稿
- 每一輪改動的審核與否決
- 是否上線、是否開源、對外發佈

## 四、品質與審核流程

1. AI 產出的改動先在本地分支完成，不直接進入 `main`。
2. 每次合併前必須通過：`sloplint` 靜態檢查、`node --check` 語法檢查、瀏覽器實測（iPad 四種尺寸）。
3. 涉及資料庫或部署設定的改動，需在生產環境以實際請求驗證（例如 `live == local` 位元組比對、API 200 回應）。
4. 作者對每一項視覺與行為結果作最終判斷；不符合預期的改動會被還原，而非「將就保留」。

## 五、第三方素材

AI 沒有引入任何閉源、來源不明或授權不相容的程式碼與素材。

- 動物圖示：**Twemoji**（CC-BY 4.0），見 [`NOTICE.md`](NOTICE.md)
- 依賴套件：見 [`requirements.txt`](requirements.txt)，各自依原授權（MIT / BSD / Apache-2.0）
- 字體：沒有內嵌字體檔

## 六、對使用者的提示

1. 本軟件按「現狀」提供，不附任何明示或隱含保證；詳見 [`LICENSE`](LICENSE)。
2. AI 協助產生的程式碼可能含有錯誤或安全弱點。若你將本軟件用於公開場合或生產環境，請自行覆核並按需要加固。
3. 若發現錯誤、安全問題或不準確的聲明，請依 [`SECURITY.md`](SECURITY.md) 或 GitHub Issues 提出。

## 七、聲明的變更

本聲明如有更新，會在本檔案頂部遞增版本號並記錄於 Git 歷史；
重大變更將於 [`README.md`](README.md) 的版本說明中註明。

---

## English Summary

This project was developed with the assistance of an **AI coding agent**.

- **Agent framework:** Hermes Agent (Nous Research)
- **Model access:** OpenCode (Go plan)
- **Language model:** DeepSeek V4.1 Flash

All product decisions, design choices, content, review, testing and release decisions
were made by the author, **Leung Tung Lam**, who takes full responsibility for the software.
The AI acted solely as an implementation tool and is not a co-author.

No closed-source or unknown-origin third-party code or assets were introduced by the AI.
Third-party attributions are listed in [`NOTICE.md`](NOTICE.md); licensing terms are in [`LICENSE`](LICENSE).
