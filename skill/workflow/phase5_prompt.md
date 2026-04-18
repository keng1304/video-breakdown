# Phase 5 — Claude Vision 產 Prompt

最後一步：把每個 shot 的關鍵幀 + Phase 3/4 分析資料送 Claude Vision，讓它**看圖說話**，產出可直接用的 Prompt。

## 模組位置
- `src/director/prompt/keyframe_selector.py` — 關鍵幀挑選
- `src/director/prompt/claude_vision.py` — Claude API 視覺分析
- `src/director/prompt/prompt_formatter.py` — 格式化為 Seedance / Kling

## 流程

```
for each shot:
  1. 取關鍵幀（通常取第 2 張 = 中段）
  2. 送 Claude Vision API + 附 Phase 3/4 的原始資料
  3. Claude 輸出 3 種格式：
     - seedance_prompt (英文，可直接給 Higgsfield 生圖)
     - kling_prompt (英文，可直接給 Kling 生影片)
     - zh_description (中文，給客戶看的敘述)
```

## Prompt 模板（送給 Claude Vision）

```
你是專業的影像 prompt 工程師。看這張關鍵幀 + 下列技術資料，產出可直接使用的 prompt。

技術資料：
- 鏡頭編號：S-03
- 時長：2.5s
- 景別：medium
- 運鏡：pan_right
- 人數：1
- 主色調：#D4A574 / #F5E6D3 / #8B4513
- 整支片風格：溫暖治癒

請輸出 JSON：
{
  "seedance_prompt": "...",
  "kling_prompt": "...",
  "zh_description": "..."
}

規則：
- Seedance prompt 英文，含 主體 + 場景 + 動作 + 光線 + 色彩 + 運鏡
- Kling prompt 要注重「動態」，包含動作動詞
- 中文描述要白話，給客戶看
```

## 輸出示例

```json
{
  "shot_index": 0,
  "seedance_prompt": "Wide shot of industrial-style photo studio with red brick walls and large factory windows, golden hour sunlight streaming through, warm amber and cream palette, leading lines composition, pan right camera motion revealing vintage sofa and plants, Vermeer-inspired lighting",
  "kling_prompt": "Camera panning right slowly across industrial studio space, golden sunlight moving across red brick wall, slight movement of plant leaves in breeze, atmospheric dust particles floating in light beams",
  "zh_description": "廣角鏡頭，工業風攝影棚帶紅磚牆和大窗戶，金黃陽光灑入，右搖鏡頭揭示復古沙發和植栽"
}
```

## 成本

每 shot 送一次 Claude Vision = 1 張圖 + 1500 tokens 回覆：
- Claude Sonnet 4.6：約 $0.02 / shot
- 30 shots（約 1 支 2 分鐘片）= $0.60

## Batch 模式（省 token）

可以一次送 5 shots 給 Claude：
```
shots_batch = [shot1_keyframe, shot2_keyframe, ...]
prompt = "請為這 5 個 shots 分別產 prompt，輸出 JSON array"
```

省下多次 system prompt 的成本。

## 跟其他 skills 的串接

### 串到 director-proposal（🎬 導演）
產好 Phase 5 的 prompts → 當作「已確認腳本」塞給導演 skill 做提案

### 串到 video-director-agent（🎞️ 影像專案）
用拆出來的 Seedance prompts 當作 Phase 4 彩圖的起點

### 串到 aesthetics-extended（🎨 風格細節）
若 Claude Vision 輸出的 prompt 還不夠細，去美學庫補大師光/大師運鏡

## 可選：跳過 Claude Vision

如果只是要 shot list、不要 prompt，可以：
```bash
.venv/bin/director analyze video.mp4 --skip-claude
```
只跑到 Phase 4，輸出含 fingerprint 但不含 prompts。這樣成本 = $0（純本地運算）。
