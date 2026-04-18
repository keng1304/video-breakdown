# Phase 3 — 多維分析（per-shot）

每個 shot 同時跑 4 條分析管線，產出完整的技術資料。

## 4 條管線

### 1. 運鏡分析 (Camera Motion)
- **模組**：`src/director/perception/camera.py`
- **技術**：RAFT-Small ONNX + OpenCV Homography 分解
- **加速**：CoreML EP（M 系列晶片）
- **Fallback**：OpenCV Farneback optical flow
- **輸出**：
  - `static`（靜止）/ `pan_left`/`pan_right`/`tilt_up`/`tilt_down`
  - `zoom_in`/`zoom_out`/`dolly_in`/`dolly_out`
  - `handheld`（手持晃動）/`rotate`（旋轉）

### 2. 姿態分析 (Pose)
- **模組**：`src/director/perception/pose.py`
- **技術**：RTMPose via rtmlib（純 ONNX）
- **Detection 模型**：rtmdet-nano
- **Pose 模型**：rtmpose-m
- **輸出**：
  - `pose_count`：畫面人數
  - `keypoints`：17 關節點（COCO 格式）
  - **用途**：判斷是否為人物鏡頭、近景特寫 vs 全身

### 3. 景別分析 (Shot Size)
- **技術**：基於 pose keypoints 推論（人臉佔畫面比例）
- **7 級景別**：
  - `extreme_close_up` — 大特寫（佔畫面 >60%）
  - `close_up` — 特寫（30-60%）
  - `medium_close_up` — 中特寫（20-30%）
  - `medium` — 中景（10-20%）
  - `medium_wide` — 中全景（5-10%）
  - `wide` — 全景（2-5%）
  - `extreme_wide` — 大全景（<2%）

### 4. 色彩分析 (Color Palette)
- **技術**：K-means 5 色提取 + 命中 COLOR_PALETTES 詞彙庫
- **輸出**：
  - Top 5 hex colors
  - 命中的色彩詞彙（`溫暖治癒`、`都會專業`、`熱情活力` 等）

## 音訊（全局）

**模組**：`src/director/perception/audio.py` + `music_structure.py`
**技術**：librosa

輸出：
- **BPM**（60-180 之間的節拍）
- **Beat onset times**（每個 beat 的時間點）
- **音樂結構**：intro / verse / build / drop / outro（相對於影片時長）
- **音樂情緒**：命中 MUSIC_EMOTIONS 詞彙（溫暖治癒/活力熱情/科技冷感...）

## Python 呼叫（完整 pipeline）

```python
from director.generate.swap_pipeline import _analyze_reference_video
from director.config import get_config

cfg = get_config()
analysis_path = _analyze_reference_video("path/to/video.mp4", cfg)
# → output/{name}_analysis.json
```

內部會自動串 scene → camera → pose → color → audio → fingerprint → prompt。

## 記憶體

每條管線 load → process → unload（sequential，不並行）：

| 管線 | Peak RAM |
|---|---|
| TransNetV2 | ~500MB |
| RAFT-Small | ~1.5GB |
| RTMPose | ~800MB |
| librosa | ~200MB |
| **任一時刻峰值** | **~1.5GB** |

M3 Pro 128GB 綽綽有餘。

## 輸出示例

```json
"shots": [
  {
    "shot_index": 0,
    "start_sec": 0.0,
    "end_sec": 3.2,
    "camera_motion": "pan_right",
    "pose_count": 0,
    "composition": {
      "shot_size": "wide",
      "composition_rule": "leading_lines",
      "color_palette": ["#D4A574", "#F5E6D3", "#8B4513", "#FFB703", "#6B4423"],
      "color_palette_names": ["溫暖治癒", "amber"]
    }
  },
  ...
]
```

音訊全局：

```json
"audio": {
  "bpm": 76,
  "beats_sec": [0.0, 0.79, 1.58, ...],
  "structure": [
    {"section": "intro", "start": 0.0, "end": 4.0},
    {"section": "verse", "start": 4.0, "end": 15.0},
    {"section": "build", "start": 15.0, "end": 22.0},
    {"section": "drop", "start": 22.0, "end": 28.0},
    {"section": "outro", "start": 28.0, "end": 30.5}
  ],
  "emotion": "溫暖治癒"
}
```

## 下一步

→ Phase 4 跨 shot 彙整成風格指紋
