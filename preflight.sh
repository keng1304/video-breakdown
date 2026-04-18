#!/usr/bin/env bash
# video-breakdown — 環境檢查。失敗時回報缺什麼。
set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

FAIL=0
check() {
  if eval "$2" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} $1"
  else
    echo -e "${RED}✗${NC} $1"
    FAIL=1
  fi
}

echo "== video-breakdown preflight =="
check "macOS"                      '[[ "$(uname)" == "Darwin" ]]'
check "Apple Silicon"              '[[ "$(uname -m)" == "arm64" ]]'
check "Homebrew"                   'command -v brew'
check "yt-dlp"                     'command -v yt-dlp'
check "ffmpeg"                     'command -v ffmpeg'
check "uv"                         'command -v uv'
check ".venv"                      '[[ -d "$REPO_ROOT/.venv" ]]'
check ".env 存在"                   '[[ -f "$REPO_ROOT/.env" ]]'
check "ANTHROPIC_API_KEY 已設"      'grep -q "^ANTHROPIC_API_KEY=..*" "$REPO_ROOT/.env"'
check "video-breakdown CLI"        '"$REPO_ROOT/.venv/bin/video-breakdown" --version'

if [[ $FAIL -eq 0 ]]; then
  echo -e "\n${GREEN}全部通過，可以使用。${NC}"
  exit 0
else
  echo -e "\n${RED}有項目失敗。${NC}請先跑 ./install.sh 或編輯 .env 補 API Key。"
  exit 1
fi
