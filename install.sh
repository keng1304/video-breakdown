#!/usr/bin/env bash
# video-breakdown — One-shot installer
# 只支援 macOS Apple Silicon。
set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'
info()  { echo -e "${GREEN}▸${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo ""
echo "════════════════════════════════════════════════"
echo "  video-breakdown installer"
echo "════════════════════════════════════════════════"
echo ""

# ── 1. 檢查 macOS + Apple Silicon ─────────────
info "檢查系統..."
if [[ "$(uname)" != "Darwin" ]]; then
  error "這個 skill 只支援 macOS。偵測到：$(uname)"
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  error "這個 skill 只支援 Apple Silicon (M1/M2/M3/M4)。偵測到：$(uname -m) — Intel Mac 暫不支援。"
fi
info "macOS Apple Silicon ✓"

# ── 2. 檢查 / 安裝 Homebrew ───────────────────
if ! command -v brew >/dev/null 2>&1; then
  warn "找不到 Homebrew。要現在安裝嗎？（會需要 sudo）"
  read -p "  y/n: " yn
  if [[ "$yn" == "y" ]]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  else
    error "Homebrew 是必要依賴。請去 https://brew.sh 手動裝後再執行。"
  fi
fi
info "Homebrew $(brew --version | head -1 | cut -d' ' -f2) ✓"

# ── 3. 系統依賴（brew 套件）──────────────────
NEED_BREW=()
for pkg in yt-dlp ffmpeg; do
  if ! brew list "$pkg" >/dev/null 2>&1; then
    NEED_BREW+=("$pkg")
  fi
done
# Python 3.11（torch 限制 Python < 3.12）
if ! command -v python3.11 >/dev/null 2>&1 && ! brew list python@3.11 >/dev/null 2>&1; then
  NEED_BREW+=("python@3.11")
fi

if [[ ${#NEED_BREW[@]} -gt 0 ]]; then
  info "安裝 brew 套件：${NEED_BREW[*]}"
  brew install "${NEED_BREW[@]}"
fi
info "yt-dlp / ffmpeg / python@3.11 ✓"

# ── 4. uv（Python 套件管理器）───────────────
if ! command -v uv >/dev/null 2>&1; then
  info "安裝 uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
info "uv $(uv --version 2>&1 | cut -d' ' -f2) ✓"

# ── 5. 建 venv + 裝 Python deps ──────────────
info "建立 Python 虛擬環境 + 安裝套件（約 2-5 分鐘）..."
uv sync
info "Python 環境 ✓"

# ── 6. 建立 .env 檔（如還沒有）────────────
if [[ ! -f "$REPO_ROOT/.env" ]]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  warn ".env 剛建立，請編輯並填入你的 ANTHROPIC_API_KEY："
  echo "      $REPO_ROOT/.env"
  echo "    API Key 取得：https://console.anthropic.com"
fi

# ── 7. Symlink skill 到 Claude Code ─────────
SKILL_SRC="$REPO_ROOT/skill"
SKILL_DEST="$HOME/.claude/skills/video-breakdown"

if [[ -d "$SKILL_SRC" ]]; then
  mkdir -p "$HOME/.claude/skills"
  if [[ -L "$SKILL_DEST" ]] || [[ -d "$SKILL_DEST" ]]; then
    warn "$SKILL_DEST 已存在，將覆蓋"
    rm -rf "$SKILL_DEST"
  fi
  ln -s "$SKILL_SRC" "$SKILL_DEST"
  info "Skill 連結到 $SKILL_DEST ✓"
else
  warn "找不到 $SKILL_SRC — skill 檔案可能缺失"
fi

# ── Done ─────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ 安裝完成${NC}"
echo "════════════════════════════════════════════════"
echo ""
echo "下一步："
echo "  1. 編輯 ${YELLOW}$REPO_ROOT/.env${NC} 填入 ANTHROPIC_API_KEY"
echo "  2. 重開 Claude Code"
echo "  3. 在 Claude Code 說：「拆解這支片 <YouTube 連結>」"
echo ""
echo "模型檔第一次執行時會自動從 Hugging Face / torch hub 下載（約 500MB-1GB）。"
echo ""
