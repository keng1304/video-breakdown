---
name: video-breakdown
description: 🔍 影片拆解 — 貼連結或本地檔即可全自動分析影片：鏡頭切分、關鍵幀截取、運鏡軌跡、景別偵測、色彩指紋、音樂結構，最後用 Claude Vision 產出每鏡描述 + Seedance/Kling prompt。當使用者丟一支影片問「這怎麼拍的」「幫我分析」「我想複製這個感覺」時觸發。觸發關鍵字：「影片拆解」「拆解影片」「分析影片」「拆這支」「這支片怎麼拍的」「參考片分析」「鏡頭分析」「運鏡分析」「reverse engineer」「breakdown this video」「怎麼拍的」「競品怎麼拍」。
---

# Video Breakdown — 參考影片分析引擎

把任何一支影片（YouTube / Vimeo / IG Reels / 本地檔）變成**結構化資料**：
- 鏡頭切分 + 每鏡秒數
- 每鏡關鍵幀截圖
- 運鏡軌跡（推/拉/搖/軌道/手持/空拍）
- 景別（大特寫 / 特寫 / 中景 / 全景 / 大全景）
- 色彩指紋（主色調 top-5）
- 音樂結構（intro / verse / drop / outro, BPM）
- 每鏡 Seedance / Kling prompt（可直接拿去生類似影片）

## 前提

此 skill 綁本地 Python 專案（透過 `install.sh` 安裝的 video-breakdown repo）。
執行前請確認：
- 已跑過 `./install.sh`（安裝 brew 依賴 + uv + Python 套件）
- `.env` 已填入 `ANTHROPIC_API_KEY`
- preflight 通過：`./preflight.sh`

repo 路徑由環境變數 `VIDEO_BREAKDOWN_ROOT` 指定，預設為 `$HOME/video-breakdown`。

---

## 標準流程（5 階段）

### 🎞️ Phase 1 — 取得影片
- 貼 YouTube / Vimeo / IG / 雲端連結 → `yt-dlp` 下載
- 或本地檔直接指向路徑

### ✂️ Phase 2 — 鏡頭切分 + 關鍵幀
- TransNetV2（PyTorch MPS）做 shot boundary detection
- Fallback: PySceneDetect ContentDetector

### 🎥 Phase 3 — 多維分析（per-shot）
- **運鏡**：RAFT-Small ONNX → Homography 分解
- **姿態**：RTMPose (rtmlib ONNX)
- **景別**：人臉 / 全身比例推論
- **色彩**：K-means 5 色提取
- **音訊**：librosa BPM + beat + 結構

### 🎨 Phase 4 — 風格指紋
跨 shot 統計 cuts per minute、dominant shot sizes、signature camera moves、color fingerprint、music emotion。

### 📝 Phase 5 — Claude Vision 產 Prompt
每鏡關鍵幀送 Claude Vision，產 Seedance / Kling prompt + 中文描述。

---

## 快速呼叫

### CLI

```bash
cd "$VIDEO_BREAKDOWN_ROOT"   # 預設 ~/video-breakdown
.venv/bin/video-breakdown analyze "<影片 URL 或本地路徑>"
```

常用 flag：
- `--skip-pose` 跳過人體骨架（加速）
- `--skip-audio` 跳過音頻分析
- `--no-prompts` 只拆鏡不燒 Claude token
- `-o output/` 指定輸出目錄

### 檢視結果

```bash
.venv/bin/video-breakdown report output/<video_name>_analysis.json
.venv/bin/video-breakdown report output/<video_name>_analysis.json --prompts
```

---

## 重要提醒

1. **參考影片不要超過 3 分鐘**：3 分鐘約 5-8 分鐘可跑完
2. **Claude Vision 是可選**：Phase 5 會燒 token，只要拆鏡頭可加 `--no-prompts`
3. **垂直影片（IG Reels）支援**：自動偵測 9:16
4. **不支援直播串流**：要完整 mp4 檔
5. **首次執行會下載模型**：TransNetV2 / RAFT / RTMPose 自動下載到 `~/.cache/`（約 500MB-1GB）

---

## 子檔案索引

| 檔案 | 何時讀 |
|---|---|
| [workflow/phase1_download.md](workflow/phase1_download.md) | 各種影片來源處理 |
| [workflow/phase2_decompose.md](workflow/phase2_decompose.md) | 鏡頭切分細節 |
| [workflow/phase3_analyze.md](workflow/phase3_analyze.md) | 運鏡/景別/色彩/音訊分析 |
| [workflow/phase4_fingerprint.md](workflow/phase4_fingerprint.md) | 風格指紋邏輯 |
| [workflow/phase5_prompt.md](workflow/phase5_prompt.md) | Claude Vision + Seedance/Kling 格式 |
| [tools/cli_usage.md](tools/cli_usage.md) | CLI 指令大全 |
