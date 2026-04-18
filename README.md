# video-breakdown

把任何一支影片拆解成可複製的結構化資料 — 鏡頭切分、運鏡軌跡、景別、色彩指紋、音樂結構，最後產出每鏡 Seedance / Kling prompt。

**適合誰用**：想分析競品、學一支廣告怎麼拍、拿到一支 reference 想反推 prompt 的創作者 / 導演 / 行銷。

---

```
$ video-breakdown analyze "https://www.youtube.com/watch?v=XXXX"

▸ 下載影片...                  ✓ 45.2s / 1920x1080 / 24fps
▸ 鏡頭切分 (TransNetV2)...     ✓ 偵測到 28 鏡
▸ 關鍵幀截取...                 ✓ 84 張
▸ 運鏡分析 (RAFT)...           ✓ pan 9 / static 12 / zoom 4 / handheld 3
▸ 姿態偵測 (RTMPose)...        ✓ 19 鏡含人，平均 1.4 人
▸ 色彩指紋 (K-means)...        ✓ 溫暖治癒 / amber / cream
▸ 音樂結構 (librosa)...         ✓ 76 BPM / intro-verse-drop-outro
▸ Claude Vision 產 prompt...   ✓ 28 組 Seedance + Kling prompt

分析完成！
  輸出: output/reference_analysis.json
  鏡頭: 28  |  Prompt: 28  |  風格: 中速 (12.5 剪/分鐘)
  費用: $0.87 USD
```

**輸出範例**（節錄一鏡）：
```json
{
  "shot_index": 3,
  "start_sec": 8.4,
  "end_sec": 11.2,
  "composition": {
    "shot_size": "medium_close_up",
    "color_palette": ["#D4A574", "#F5E6D3", "#8B4513"]
  },
  "camera_motion": "pan_left",
  "seedance_prompt": "Medium close-up of a woman's hands adjusting camera dials, warm amber lighting from window-left, shallow depth of field, 35mm lens feel, slow pan left revealing industrial workshop background...",
  "zh_description": "中近景帶人物雙手調整相機轉盤，窗外暖琥珀光打左側，淺景深，35mm 焦段感，慢慢左搖揭露工業風工作室背景"
}
```

---

## 安裝（一次性）

### 前置條件
- **macOS Apple Silicon**（M1 / M2 / M3 / M4）— 第一版不支援 Intel Mac
- 已安裝 [Claude Code](https://claude.com/claude-code)
- [Anthropic API Key](https://console.anthropic.com)

### 一鍵安裝

```bash
git clone <this-repo-url> ~/video-breakdown
cd ~/video-breakdown
./install.sh
```

`install.sh` 會自動處理：
1. 檢查 macOS Apple Silicon
2. 裝 Homebrew（若沒有）
3. 裝 `yt-dlp` / `ffmpeg` / `python@3.11`
4. 裝 `uv`（Python 套件管理器）
5. 建立 venv + 安裝所有 Python 套件
6. 建 `.env` 範本
7. 把 skill 連結到 Claude Code

然後編輯 `.env` 填入你的 `ANTHROPIC_API_KEY`。

### 驗證

```bash
./preflight.sh
```

全綠就代表裝好了。

## 使用

重開 Claude Code，貼：

> 拆解這支片 https://www.youtube.com/watch?v=...

或

> 幫我分析這支 Reels [本地路徑 .mp4]

Claude 會自動呼叫 `video-breakdown` skill 跑完 5 階段。

## 輸出

`output/{video_name}_analysis.json` 包含：
- 每鏡起訖秒數 + 景別 + 運鏡 + 色彩
- 整片 fingerprint（cuts per minute, dominant shot sizes, color palette）
- 音樂結構（BPM, intro/verse/drop/outro）
- 每鏡 Seedance + Kling prompt + 中文描述

關鍵幀存在 `output/keyframes/`。

## 首次執行會下載的東西

- **TransNetV2 模型**（~100MB）— 鏡頭切分
- **RAFT-Small ONNX**（~50MB）— 運鏡分析
- **RTMPose ONNX**（~50MB）— 人體骨架
- 其他 torch hub checkpoints（~200-500MB）

全部自動抓到 `~/.cache/`，只會下載一次。

## 預期時間

| 影片長度 | 分析時間 |
|---|---|
| 30 秒 | 1-2 分鐘 |
| 1 分鐘 | 3-5 分鐘 |
| 3 分鐘 | 8-12 分鐘 |

## 成本

Claude Vision（Phase 5）每鏡約 $0.01-0.03 USD。
3 分鐘片（約 30-60 鏡）單次跑約 **$0.3-2 USD**。
想省錢可加 `--no-prompts` 跳過 Claude Vision，只拿結構化指紋。

## 疑難排解

- **`command not found: uv`** → 重開 terminal
- **`ModuleNotFoundError`** → 在 repo 目錄跑 `uv sync`
- **Claude 找不到 skill** → 重開 Claude Code，或檢查 `~/.claude/skills/video-breakdown` 是否為 symlink
- **下載 YouTube 失敗** → `brew upgrade yt-dlp`
- **分析卡住** → 影片超過 3 分鐘通常會很慢，先剪到 3 分鐘內

## 授權

MIT — 自由使用、修改、散佈。署名 `tzukao.com`。
