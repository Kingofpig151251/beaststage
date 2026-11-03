# 版權與第三方素材

## 本項目

大電視（Big TV）— 派對猜詞主持台
Copyright (c) 2026 **Leung Tung Lam**

授權：**MIT**，全文見根目錄 [`LICENSE`](LICENSE)。

## AI 開發聲明

本項目的**設計方向、功能取捨、內容定稿與發佈決定**由作者 Leung Tung Lam 負責；
程式碼與文案在 **AI 編碼助理（Hermes Agent，背後為大型語言模型）**協助下生成與修改，
每一輪改動均經作者審核後才合併。

- 由 AI 協助的部分：版面與樣式實作、互動邏輯、API 與資料層、文案草稿
- 由人決定的部分：產品方向、資訊架構、視覺取向、內容與題目、是否上線
- 第三方素材與授權見下節；AI 沒有引入任何閉源或不明來源的素材

如你重用本項目的程式碼，請自行覆核在你情境下的正確性與安全性。

## 第三方素材

| 素材 | 用途 | 授權 | 出處 |
|---|---|---|---|
| **Twemoji** | 8 個動物圖示（🐢🦊🐳🐙🐝🦩🐬🐻），以內嵌 SVG 形式放在 `index.html` 的 `ICONS` 物件 | **CC-BY 4.0** | <https://github.com/jdecked/twemoji> |

Twemoji 圖形由 Twitter, Inc. 及其他貢獻者製作，以 CC-BY 4.0 授權發布；
本項目只作原樣內嵌，沒有修改圖形本身。如要再利用，請保留上述標註。

## 字體

本項目**沒有內嵌任何字體檔**。介面使用 `system-ui`，在 Apple 裝置上解析為
SF Pro（Apple Inc.，屬系統字體，隨裝置授權，不隨本項目轉授）。

## 依賴

見 `requirements.txt`（FastAPI、psycopg 等），各自依其原本授權（多為 MIT / BSD / Apache-2.0）。
