# Handoff — Keng 上架指令

打包完成。下一步靠你手動跑（gh 需要互動授權 + private repo 決策）。

## 成品位置
```
~/tzukao_ship/video-breakdown-ship-v1/
├── src/director/       # 去業務化後的引擎（保留 input/perception/structure/fingerprint/prompt/aesthetics/utils）
├── skill/              # 客戶的 Claude Code skill（去識別化）
├── install.sh          # 一鍵裝
├── preflight.sh        # 環境檢查
├── .env.example        # API key 範本
├── .gitignore          # 排除 .env / models / output / venv
├── README.md           # 客戶視角
├── LICENSE             # Proprietary（禁轉售）
├── CHANGELOG.md
└── pyproject.toml
```

## 客戶拿到後的流程
```bash
git clone <private-repo-url> ~/video-breakdown
cd ~/video-breakdown
./install.sh
# 填 .env 的 ANTHROPIC_API_KEY
./preflight.sh   # 全綠就 ok
# 重開 Claude Code → 「拆解這支片 <YT 連結>」
```

## GitHub private repo 開設（複製貼上跑）
```bash
cd ~/tzukao_ship/video-breakdown-ship-v1
git init
git add -A
git commit -m "v1.0 — initial shippable release"

# 用 gh 建 private repo（需先 gh auth login）
gh repo create video-breakdown --private --source=. --push --description "Turn any reference video into structured shot data + AI prompts"
```

## 客戶端安裝前先做一次自己的煙霧測試

建議你自己先在乾淨 terminal 跑一次：
```bash
cd ~/tzukao_ship/video-breakdown-ship-v1
./install.sh            # 約 2-5 分鐘
./preflight.sh          # 應該全綠
.venv/bin/video-breakdown --help   # 應該列 5 個 command
# 找一支短片試拆
.venv/bin/video-breakdown analyze "https://www.youtube.com/shorts/XXXX" --no-prompts
```

若有報錯，回報給工程部門（skill: engineering-shipper）。

## 送給客戶的訊息模板

> 這是你剛剛私訊我那個拆片工具。
>
> 裝的方式：
> 1. 點這個 repo link → 右上角 Code → Download ZIP（或 git clone）
> 2. 解壓到 ~/video-breakdown
> 3. 打開 Terminal cd 進去，跑 `./install.sh`
> 4. 照畫面指示填 .env 的 ANTHROPIC_API_KEY
> 5. 重開 Claude Code，說「拆解這支片 <貼連結>」
>
> 只支援 Mac M 系列（M1/M2/M3/M4）。
> 有任何問題直接回我。

## Gate 0 核對
- [x] 原 `~/Documents/影像流自動化/visual-engine/` 無任何 tracked 檔案被改動（git status 乾淨）
- [x] 無 `.env` 殘留（API key 不會洩漏）
- [x] 無絕對路徑（`/Users/keng/` 全清）
- [x] 無客戶名稱
- [x] 業務代碼（ugc_workflow / photo_workflow / anchor / sync / workflow_v5 / generate）全數剝離

## 往後 v2 可以加

- 模型預下載腳本（省客戶首次等待）
- Intel Mac 支援
- Gradio UI（回加 app_video_analyzer.py，但要改成不依賴 anchor）
- 用量統計回傳（Keng 想知道哪些人在用）
