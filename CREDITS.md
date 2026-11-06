# 素材來源與授權（Assets & Credits）

本 repo 的**程式碼**以 MIT License 授權（見 [`LICENSE`](LICENSE)）。
**音效與圖像素材不屬於 MIT 授權範圍**，各自依下列原始授權使用。

## 音效（`sfx/`）

| 檔案 | 用途 | 來源 | 授權 |
|---|---|---|---|
| `dingdong.mp3` | 判定「正確」 | Wikimedia Commons《Doorbell-cheap-dingdong》 | Public domain |
| `whoosh.mp3` | 判定「跳過」 | 本項目自製（掃頻噪音） | 同本 repo（MIT） |
| `snare.mp3` | 判定「犯規」／冠軍重擊 | OpenGameArt《An interesting snare drum sound》 | CC0 1.0 |
| `countdown.mp3` | 倒數 3-2-1 與開始 | OpenGameArt《race start countdown》 | CC0 1.0 |
| `whistle.mp3` | 時間到 | SpliceSound 裁判哨 | CC0 |
| `settle.mp3` | 回合結算 | OpenGameArt《Classic fanfare lick》(fanfare_3) | CC0 1.0 |
| `tick.mp3` | 結果頁揭曉／倒數滴答 | Wikimedia Commons《Clock ticking》(pdsounds.org) | Public domain |
| `hb3.mp3` | 倒數心跳 | Wikimedia Commons《Human heart beating at 61 bpm》，原錄音 **Benboncan**（Freesound） | **CC BY 3.0** |
| `drums.mp3` | 冠軍前鼓聲 | OpenGameArt《Horde War Drums》(William Hector) | CC0 1.0 |
| `champion.mp3` | 冠軍背景音樂 | **Kevin MacLeod**《Celebration》([incompetech.com](https://incompetech.com)) | **CC BY 4.0** |
| `tap.mp3` | 通用按鍵音 | 本項目自製 | 同本 repo（MIT） |

### 需要署名的兩項（CC BY）

- `hb3.mp3` — 「Human heart beating at 61 bpm」 by **Benboncan**（Freesound），透過 Wikimedia Commons，**CC BY 3.0**。本項目作了裁剪、升調 5× 與音量正規化。
- `champion.mp3` — 「Celebration」 by **Kevin MacLeod** (incompetech.com)，**CC BY 4.0**。本項目節錄 8 小節並做成無縫 loop。

授權全文：
- CC BY 3.0 — https://creativecommons.org/licenses/by/3.0/
- CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
- CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/

## 圖像（`art/team/`、`icon-*.png`、`favicon.ico`）

由 SenseNova 圖像模型生成，本項目自行去背、裁切與縮放。無第三方素材。

## 重新使用時要注意

- MIT 只覆蓋程式碼。你可以自由 fork 程式碼，但**不能把上述 CC BY 素材改成 MIT**。
- 保留 `sfx/` 內素材時，必須一併保留本檔（或等效的署名與授權說明）。
- 若不想處理署名，最簡單的做法是刪走 `hb3.mp3` 與 `champion.mp3`，換成 CC0 素材或自製音效。
