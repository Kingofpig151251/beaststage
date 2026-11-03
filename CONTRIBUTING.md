# 貢獻指南 / Contributing

多謝你考慮為「大電視」出一分力。本項目以 MIT 授權開源。

## 回報問題

- 用 GitHub Issues，一件事一個 issue。
- 請包括：iPad 型號／瀏覽器版本、重現步驟、預期與實際結果、截圖（如適用）。
- 安全相關問題**不要**開公開 issue，請依 [`SECURITY.md`](SECURITY.md)。

## 提交改動

1. Fork，並從 `main` 開分支：`fix/…`、`feat/…`、`docs/…`。
2. 本項目**沒有 build step**：`index.html`、`edit.html` 就是成品，直接用瀏覽器開即可。
3. 提交前請自行跑一次檢查（見下）。
4. PR 說明寫清楚：改了什麼、為什麼、如何驗證（附量測數字或截圖更好）。

## 本地檢查

```bash
# 語法
python3 -c "s=open('index.html').read(); open('/tmp/c.js','w').write(s[s.rindex('<script>')+8:s.rindex('</script>')])"
node --check /tmp/c.js

# 版面／無障礙靜態檢查（需要 hallmark skill 的 sloplint.mjs）
node sloplint.mjs index.html --scope app
node sloplint.mjs edit.html --scope app

# 本地後端（可選）
python3 tests/mock_sync_server.py   # http://127.0.0.1:8899
```

## 設計公約（重要）

本項目的視覺與文案有既定取向，改動前請先讀 [`docs/design-spec.md`](docs/design-spec.md)。

- **文案一律繁體書面語**，不用粵語口語（例：「返回」而非「返」）。
- 介面只用 `system-ui`，不引入網絡字體。
- 單檔交付：不引入前端框架、bundler 或額外 CSS 檔。
- 顏色、字階、間距一律走 CSS token（`:root`），不要寫死色值。
- 舞台優先：出題畫面只有一個大字，分數與裝飾不出現在該畫面。
- 動物圖示與隊色一一綁定，且不可重複使用。

## AI 輔助貢獻

本項目本身接受 AI 輔助開發（見 [`AI-DISCLOSURE.md`](AI-DISCLOSURE.md)）。
如你的 PR 主要由 AI 生成，請在描述中註明使用的工具與模型，並確認你已親自覆核每行改動。
