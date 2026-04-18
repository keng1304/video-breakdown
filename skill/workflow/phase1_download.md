# Phase 1 — 取得影片

支援 3 種來源：
1. YouTube / Vimeo 連結
2. IG Reels / TikTok 連結
3. 本地檔案路徑

## Python API

### YouTube / Vimeo / IG / TikTok

```python
from director.input.downloader import resolve_video
from pathlib import Path

url = "https://www.youtube.com/watch?v=XXXX"
local_path = resolve_video(url, output_dir=Path("output/downloads"))
# → /path/to/output/downloads/example_video.mp4
```

### 本地檔案

```python
from pathlib import Path
vp = Path("/path/to/local.mp4")
# 直接用 vp，不需要 resolve
```

## 支援格式

| 來源 | 狀態 |
|---|---|
| YouTube | ✅ yt-dlp |
| Vimeo | ✅ yt-dlp |
| IG Reels | ✅ yt-dlp |
| TikTok | ✅ yt-dlp |
| X (Twitter) | 🟡 有時候失敗（需登入） |
| Facebook | 🟡 有時候失敗 |
| Google Drive 分享連結 | ✅ gdown（需公開權限） |
| 本地 mp4 / mov | ✅ |
| 雲端 OneDrive / Dropbox | ❌ 要先下載到本地 |

## 設定

`.venv/bin/yt-dlp` 應該已內建。如果失敗：
```bash
pip install --upgrade yt-dlp
```

## 常見錯誤

### 影片太長（>10 分鐘）
分析會變慢。建議先用 ffmpeg 裁切：
```bash
ffmpeg -i input.mp4 -ss 00:00:00 -t 00:03:00 -c copy short.mp4
```

### 私人 / 未公開影片
yt-dlp 需要 cookies：
```bash
yt-dlp --cookies-from-browser chrome "https://..."
```

### 直播串流
**不支援**。要等直播結束變 VOD 才能抓。

## 下一步

檔案下載完成 → 進 Phase 2 鏡頭切分。

影片路徑存到 `_state["video_path"]`，傳給後續階段。
