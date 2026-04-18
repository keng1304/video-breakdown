"""Video URL downloader — YouTube, Instagram Reels, cloud links."""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

# Supported URL patterns
_YOUTUBE_RE = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)'
)
_INSTAGRAM_RE = re.compile(
    r'(https?://)?(www\.)?instagram\.com/(reel|reels|p)/'
)
_TIKTOK_RE = re.compile(
    r'(https?://)?(www\.|vm\.)?tiktok\.com/'
)
_DIRECT_VIDEO_RE = re.compile(
    r'https?://.+\.(mp4|mov|webm|avi|mkv)(\?.*)?$', re.IGNORECASE
)


def is_url(text: str) -> bool:
    """Check if input looks like a URL rather than a file path."""
    text = text.strip()
    return text.startswith("http://") or text.startswith("https://")


def resolve_video(input_path: str, download_dir: str | Path | None = None) -> Path:
    """Resolve input to a local video file.

    - If it's a local path → return as-is
    - If it's a URL → download and return local path

    Supports: YouTube, IG Reels, TikTok, direct video URLs, Google Drive, Dropbox, etc.
    """
    input_path = input_path.strip()

    if not is_url(input_path):
        p = Path(input_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Video file not found: {input_path}")

    # It's a URL → download
    if download_dir is None:
        download_dir = Path(tempfile.mkdtemp(prefix="director_dl_"))
    else:
        download_dir = Path(download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)

    url = input_path

    # Try yt-dlp first (handles YouTube, IG, TikTok, and many others)
    if _is_ytdlp_compatible(url):
        return _download_ytdlp(url, download_dir)

    # Direct video URL → httpx download
    if _DIRECT_VIDEO_RE.match(url):
        return _download_direct(url, download_dir)

    # Google Drive / Dropbox → try yt-dlp as fallback (it handles some of these)
    return _download_ytdlp(url, download_dir)


def _is_ytdlp_compatible(url: str) -> bool:
    """Check if yt-dlp likely supports this URL."""
    return bool(
        _YOUTUBE_RE.search(url)
        or _INSTAGRAM_RE.search(url)
        or _TIKTOK_RE.search(url)
        or "vimeo.com" in url
        or "dailymotion.com" in url
        or "twitter.com" in url
        or "x.com" in url
    )


def _download_ytdlp(url: str, download_dir: Path) -> Path:
    """Download video via yt-dlp."""
    output_template = str(download_dir / "reference.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        "--no-check-certificates",
        url,
    ]

    log.info("Downloading via yt-dlp: %s", url)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            log.error("yt-dlp stderr: %s", result.stderr[-500:])
            raise RuntimeError(f"yt-dlp failed: {result.stderr[-200:]}")
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp not found. Install with: brew install yt-dlp"
        )

    # Find the downloaded file
    files = list(download_dir.glob("reference.*"))
    if not files:
        raise RuntimeError(f"yt-dlp produced no output for {url}")

    # Prefer .mp4
    mp4s = [f for f in files if f.suffix == ".mp4"]
    result_path = mp4s[0] if mp4s else files[0]

    log.info("Downloaded: %s (%.1f MB)", result_path.name, result_path.stat().st_size / 1e6)
    return result_path


def _download_direct(url: str, download_dir: Path) -> Path:
    """Download a direct video URL via httpx."""
    import httpx

    # Guess filename from URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "reference.mp4"
    if not any(filename.endswith(ext) for ext in [".mp4", ".mov", ".webm", ".avi"]):
        filename = "reference.mp4"

    output_path = download_dir / filename
    log.info("Downloading direct URL: %s", url)

    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(8192):
                f.write(chunk)

    log.info("Downloaded: %s (%.1f MB)", output_path.name, output_path.stat().st_size / 1e6)
    return output_path


def get_url_info(url: str) -> dict:
    """Get basic info about a URL without downloading."""
    url = url.strip()

    if _YOUTUBE_RE.search(url):
        return {"platform": "YouTube", "supported": True}
    elif _INSTAGRAM_RE.search(url):
        return {"platform": "Instagram Reels", "supported": True}
    elif _TIKTOK_RE.search(url):
        return {"platform": "TikTok", "supported": True}
    elif "vimeo.com" in url:
        return {"platform": "Vimeo", "supported": True}
    elif _DIRECT_VIDEO_RE.match(url):
        return {"platform": "Direct URL", "supported": True}
    elif "drive.google.com" in url:
        return {"platform": "Google Drive", "supported": True, "note": "需要公開分享連結"}
    elif "dropbox.com" in url:
        return {"platform": "Dropbox", "supported": True, "note": "需要公開分享連結"}
    else:
        return {"platform": "Unknown", "supported": True, "note": "將嘗試 yt-dlp 下載"}
