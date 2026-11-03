# 版權與第三方素材

## 本項目

大電視（Big TV）— 派對猜詞主持台
Copyright (c) 2026 **Leung Tung Lam**

授權：**MIT**，全文見根目錄 [`LICENSE`](LICENSE)。

## AI 使用聲明

本項目在開發過程中使用 AI 編碼助理協助實作；所有產品方向、設計決定、內容定稿、
測試與發佈均由作者 **Leung Tung Lam** 負責，AI 不具備決定權，亦非共同作者。

**工具鏈：** Hermes Agent（代理框架）· OpenCode（Go 方案，模型存取）· DeepSeek V4.1 Flash（語言模型）

完整聲明（範圍、流程、第三方素材、使用者提示）見 [`AI-DISCLOSURE.md`](AI-DISCLOSURE.md)。

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
