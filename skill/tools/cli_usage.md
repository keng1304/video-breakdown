# CLI 指令大全

影片拆解引擎的所有指令。

## 位置

```bash
cd "$VIDEO_BREAKDOWN_ROOT"   # 預設 ~/video-breakdown
```

## 常用指令

### 分析 YouTube 影片
```bash
.venv/bin/video-breakdown analyze "https://www.youtube.com/watch?v=XXXX"
```

### 分析本地檔案
```bash
.venv/bin/video-breakdown analyze ./path/to/video.mp4
```

### 跳過 Claude Vision（省錢，只拆鏡頭）
```bash
.venv/bin/video-breakdown analyze video.mp4 --no-prompts
```

### 跳過特定分析
```bash
.venv/bin/video-breakdown analyze video.mp4 --skip-pose --skip-audio
```

### 指定輸出目錄
```bash
.venv/bin/video-breakdown analyze video.mp4 -o my_output/
```

### 批次分析
```bash
.venv/bin/video-breakdown batch video1.mp4 video2.mp4 video3.mp4 -o batch_output/
```

### 看結果
```bash
.venv/bin/video-breakdown report output/<video_name>_analysis.json
.venv/bin/video-breakdown report output/<video_name>_analysis.json --prompts
.venv/bin/video-breakdown report output/<video_name>_analysis.json --shot 3
```

### 查 API 費用
```bash
.venv/bin/video-breakdown cost
```

## 輸出位置

```
output/
├── {video_name}_analysis.json    # 完整分析結果
├── keyframes/
│   ├── shot_00_000.jpg           # 每 shot 的關鍵幀
│   ├── shot_00_001.jpg
│   └── ...
└── downloads/
    └── {video_name}.mp4           # 下載的原始影片（若從 URL）
```

## 環境變數

在 `.env`：
```
ANTHROPIC_API_KEY=...    # Phase 5 Claude Vision 需要
```

## 記憶體 / 時間預期

| 影片長度 | 分析時間 | 峰值 RAM |
|---|---|---|
| 30 秒 | 1-2 分鐘 | ~1.5 GB |
| 1 分鐘 | 3-5 分鐘 | ~1.5 GB |
| 3 分鐘 | 8-12 分鐘 | ~1.5 GB |
| 10 分鐘 | 30-40 分鐘 | ~1.5 GB |

Apple Silicon（M1/M2/M3/M4）實測。
