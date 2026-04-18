# Phase 4 — 風格指紋

把 Phase 3 per-shot 的原始資料，彙整成整支影片的**風格特徵**，用來：
1. 讓 AI 導演（director-proposal skill）讀懂這支參考片的調性
2. 做競品比較（A 片 vs B 片指紋差多少）
3. 指導後續自己要拍類似風格的廣告

## 模組位置
- `src/director/fingerprint/statistics.py` — 跨 shot 統計
- `src/director/fingerprint/style.py` — 風格指紋合成

## 核心指標

### 1. 節奏（Pacing）
```
cuts_per_minute = len(shots) / duration_min
```
- `cuts_per_minute < 10` → 慢節奏（藝術片/精品）
- `10-20` → 中等（商業廣告主流）
- `20-30` → 快剪（IG Reels / TikTok）
- `> 30` → 極速（MV / 動作片預告）

### 2. 常用景別（Dominant Shot Sizes）
統計 top 3 出現最多的景別：
```
["medium", "close_up", "wide"]
```
判斷：
- close_up 多 → 情感型（美妝/保養/特寫商品）
- wide 多 → 敘事型（旅遊/品牌史詩）
- medium 多 → 商業標準

### 3. 招牌運鏡（Signature Camera Moves）
top 3：
```
["pan_right", "handheld", "static"]
```
判斷：
- handheld 多 → 真實記錄感（紀錄片/生活感）
- static 多 → 精品/穩重
- dolly/zoom 多 → 電影感

### 4. 色彩指紋（Color Fingerprint）
彙整所有 shot 的 palette 後：
- Top 5 hex colors（整支片主色調）
- 命中詞彙 top 3（`溫暖治癒`/`都會專業`/`熱情活力`）

### 5. 導演風格推論
根據上述指標組合推論：
```
if 色彩="溫暖治癒" + 節奏="中慢" + 運鏡="static+handheld":
    director_style = "是枝裕和 / 宮崎駿（溫暖生活感）"
elif 色彩="力量感" + 節奏="極速" + 運鏡="handheld+zoom":
    director_style = "Scorsese 運動敘事"
elif 色彩="科技感" + 節奏="中等" + 運鏡="static+dolly":
    director_style = "Apple / Corbijn 都會專業"
```

## 輸出格式

```json
"fingerprint": {
  "pacing": "moderate",
  "cuts_per_minute": 12.5,
  "dominant_shot_sizes": ["medium", "close_up", "wide"],
  "signature_camera_moves": ["pan", "handheld", "static"],
  "color_fingerprint": ["溫暖治癒", "amber", "cream", "warm", "natural"],
  "director_style_inference": "是枝裕和溫暖生活感",
  "music": {
    "bpm": 76,
    "emotion": "溫暖治癒",
    "structure": ["intro:0-4", "verse:4-15", "drop:15-25", "outro:25-30"]
  }
}
```

## 應用：競品比較

如果客戶丟 3 支競品要你比對：

```python
A_fp = _analyze_reference_video("competitor_a.mp4", cfg)["fingerprint"]
B_fp = _analyze_reference_video("competitor_b.mp4", cfg)["fingerprint"]
C_fp = _analyze_reference_video("competitor_c.mp4", cfg)["fingerprint"]

# 比 CPM、dominant_shot_sizes、color_fingerprint
# → 找出「競品都怎麼拍」vs「我們怎麼做出差異」
```

## 應用：串到 director-proposal（🎬 導演）

Fingerprint 可直接塞給 Skill A 做提案：

```python
from director.generate.director_consultation import propose_from_reference_video
import json

with open("output/video_analysis.json") as f:
    analysis = json.load(f)

proposal = propose_from_reference_video(
    analysis,  # 含 fingerprint
    brief={"ta": "25-35 女性", "category": "美妝保養", "platform": "ig_reels"},
)
# → AI 導演會自動讀指紋，給貼合該參考片風格的提案
```

## 下一步

→ Phase 5 Claude Vision 產 Seedance/Kling prompt
