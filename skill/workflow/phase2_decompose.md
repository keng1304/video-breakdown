# Phase 2 — 鏡頭切分 + 關鍵幀

把影片拆成 N 個 shots，每個 shot 取 1-3 張關鍵幀截圖。

## 技術棧

### 主要：TransNetV2 (PyTorch MPS)
- 模型：`transnetv2-pytorch` (PyPI)
- 大小：33MB（很小）
- 速度：M3 Pro MPS 約 1 分鐘影片 / 10-15 秒處理
- 精準度：商業廣告這類乾淨剪接的影片準確率 95%+
- 位置：`src/director/perception/scene.py`

### Fallback：PySceneDetect ContentDetector
- 若 TransNetV2 失敗（PyTorch MPS 某些 edge case）自動 fallback
- 閾值：`scene_fallback_threshold=27.0`

## 關鍵幀選取

每 shot 取 3 張（首/中/尾）:
- Frame 0: shot 起始 +10%
- Frame 1: shot 中段 50%
- Frame 2: shot 結尾 -10%

關鍵幀用於：
- 視覺 QC（人眼審查）
- Phase 3 色彩／姿態分析的輸入
- Phase 5 Claude Vision 的輸入

存放位置：`output/keyframes/shot_XX_YYY.jpg`

## Python 呼叫

```python
from director.perception.scene import SceneDetector
from director.config import get_config

cfg = get_config()
detector = SceneDetector(cfg)
shots = detector.detect("path/to/video.mp4")
# shots: list[Shot] with .start_sec, .end_sec, .keyframe_paths
```

## CLI 呼叫

```bash
.venv/bin/director analyze video.mp4 --skip-claude  # 只跑 scene + 基本 perception
```

## 輸出結構

```json
"shots": [
  {
    "shot_index": 0,
    "start_sec": 0.0,
    "end_sec": 3.2,
    "duration": 3.2,
    "keyframe_paths": [
      "output/keyframes/shot_00_000.jpg",
      "output/keyframes/shot_00_001.jpg",
      "output/keyframes/shot_00_002.jpg"
    ]
  },
  ...
]
```

## 參數調整

在 `config.py` 調整：
- `scene_threshold: 0.5` — TransNetV2 confidence cutoff（0.4-0.7 之間，越低越敏感）
- `max_process_resolution: 720` — 處理前縮放到 720p（快 2-3 倍，精準度幾乎不變）
- `scene_detect_fps: 0` — 0 = 用原 fps；若要加速可設 15

## 常見失敗

### Shot 太多（> 50）
原因：影片剪接過度頻繁，或有大量閃光/快切。
解決：提高 `scene_threshold` 到 0.6-0.7。

### Shot 太少（< 3）
原因：影片太短，或是單鏡頭無剪接。
解決：這支片不需要 shot 切分，直接當作單一 shot 分析。

### TransNetV2 MPS 錯
現象：`CoreMLCompile failed` 或類似錯。
解決：改用 CPU `device="cpu"` （速度仍可接受）。

## 下一步

→ Phase 3 多維分析（運鏡/景別/色彩/姿態/音訊）
