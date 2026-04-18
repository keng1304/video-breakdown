"""影片導演分析引擎 CLI 入口。"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console

# 自動載入 .env（如果存在）
import os as _os

def _load_dotenv():
    """從專案根目錄或 cwd 載入 .env。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for p in candidates:
        if p.exists():
            for line in p.read_text().strip().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    key, val = k.strip(), v.strip()
                    # 覆蓋空值，保留已有非空值
                    if not _os.environ.get(key):
                        _os.environ[key] = val
            return

_load_dotenv()
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, show_time=False)],
    )


# ── 中文對照表 ──
PACING_ZH = {
    "fast_cut": "快剪",
    "moderate": "中等",
    "slow_burn": "慢節奏",
    "very_slow": "極慢",
    "rhythmic": "韻律型",
    "irregular": "不規則",
}

SHOT_SIZE_ZH = {
    "extreme_close_up": "大特寫",
    "close_up": "特寫",
    "medium_close_up": "中特寫",
    "medium": "中景",
    "medium_wide": "中全景",
    "wide": "全景",
    "extreme_wide": "大全景",
}

CAMERA_ZH = {
    "static": "靜止",
    "pan_left": "左搖",
    "pan_right": "右搖",
    "tilt_up": "上仰",
    "tilt_down": "下俯",
    "zoom_in": "推進",
    "zoom_out": "拉遠",
    "dolly_in": "推軌進",
    "dolly_out": "推軌退",
    "handheld": "手持",
    "rotate": "旋轉",
}

TRANSITION_ZH = {
    "hard_cut": "硬切",
    "dissolve": "溶接",
    "fade_in": "淡入",
    "fade_out": "淡出",
    "wipe": "劃接",
    "j_cut": "J-cut",
    "l_cut": "L-cut",
}


def zh(table: dict, key: str) -> str:
    return table.get(key, key)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """影片導演分析引擎 — 參考影片結構拆解 + AI 影片生成 Prompt"""
    pass


@main.command()
@click.argument("video_path")
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="輸出目錄")
@click.option("--skip-pose", is_flag=True, help="跳過人體骨架追蹤")
@click.option("--skip-audio", is_flag=True, help="跳過音頻分析")
@click.option("--skip-camera", is_flag=True, help="跳過攝影機運動分析")
@click.option("--no-prompts", is_flag=True, help="跳過 AI Prompt 生成")
@click.option("--verbose", "-v", is_flag=True, help="詳細日誌")
def analyze(video_path: str, output_dir: str | None, skip_pose: bool, skip_audio: bool,
            skip_camera: bool, no_prompts: bool, verbose: bool):
    """分析參考影片，輸出結構化 JSON + AI 生成 Prompt。"""
    setup_logging(verbose)
    log = logging.getLogger("director")

    from director.config import get_config
    from director.input.downloader import is_url, resolve_video
    from director.fingerprint.statistics import compute_fingerprint
    from director.input.decoder import create_manifest
    from director.perception.audio import AudioAnalyzer
    from director.perception.camera import CameraAnalyzer
    from director.perception.pose import PoseTracker
    from director.perception.scene import SceneDetector
    from director.prompt.claude_vision import generate_prompts
    from director.prompt.keyframe_selector import select_keyframes
    from director.structure.schema import AudioFeatures, VideoAnalysis, VideoMetadata
    from director.structure.shot_assembler import enrich_shots
    from director.structure.timeline import align_timeline
    from director.utils.memory import model_scope

    cfg = get_config()
    if output_dir:
        cfg.output_dir = Path(output_dir)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    # Support URL input
    if is_url(video_path):
        console.print(f"\n[bold]影片導演分析引擎[/bold] — 下載中 [cyan]{video_path[:60]}[/cyan]...")
        video_path = str(resolve_video(video_path, cfg.output_dir / "downloads"))

    video_path = Path(video_path).resolve()
    if not video_path.exists():
        console.print(f"[red]找不到影片: {video_path}[/red]")
        sys.exit(1)
    console.print(f"\n[bold]影片導演分析引擎[/bold] — 正在分析 [cyan]{video_path.name}[/cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        # ── Layer 0: 解碼 ──
        task = progress.add_task("解碼影片元資料...", total=None)
        manifest = create_manifest(video_path)
        metadata = VideoMetadata(
            path=str(video_path),
            filename=video_path.name,
            duration_sec=manifest.duration_sec,
            fps=manifest.fps,
            width=manifest.width,
            height=manifest.height,
            codec=manifest.codec,
            total_frames=manifest.total_frames,
            audio_path=str(manifest.audio_path) if manifest.audio_path else None,
        )
        progress.update(task, description=f"[green]已解碼[/green]: {manifest.duration_sec:.1f}秒, {manifest.fps:.1f}fps, {manifest.width}x{manifest.height}")
        progress.remove_task(task)

        # ── Layer 1: 感知管線 ──

        # 1. 音頻分析
        audio_features = AudioFeatures()
        if not skip_audio and manifest.audio_path:
            task = progress.add_task("分析音頻節奏...", total=None)
            analyzer = AudioAnalyzer()
            with model_scope("audio"):
                analyzer.load_model()
                audio_features = analyzer.process(manifest.audio_path, manifest.duration_sec)
                analyzer.unload_model()
            progress.update(task, description=f"[green]音頻[/green]: BPM={audio_features.bpm}, {len(audio_features.beat_timestamps)} 拍點")
            progress.remove_task(task)

        # 2. 場景切割
        task = progress.add_task("偵測鏡頭邊界...", total=None)
        scene_detector = SceneDetector()
        with model_scope("scene"):
            scene_detector.load_model()
            shots = scene_detector.process(
                video_path=video_path,
                fps=manifest.fps,
                total_frames=manifest.total_frames,
            )
            scene_detector.unload_model()
        progress.update(task, description=f"[green]場景切割[/green]: 偵測到 {len(shots)} 個鏡頭")
        progress.remove_task(task)

        if not shots:
            console.print("[red]未偵測到任何鏡頭，結束分析。[/red]")
            sys.exit(1)

        # 3. 攝影機運動
        camera_motions = {}
        if not skip_camera:
            task = progress.add_task("分析攝影機運動...", total=None)
            cam_analyzer = CameraAnalyzer()
            with model_scope("camera"):
                cam_analyzer.load_model()
                camera_motions = cam_analyzer.process(video_path, shots, manifest.fps)
                cam_analyzer.unload_model()
            progress.update(task, description=f"[green]攝影機[/green]: 已分析 {len(camera_motions)} 個鏡頭")
            progress.remove_task(task)

        # 4. 人體骨架
        poses = {}
        if not skip_pose:
            task = progress.add_task("追蹤人體骨架...", total=None)
            pose_tracker = PoseTracker()
            with model_scope("pose"):
                pose_tracker.load_model()
                poses = pose_tracker.process(video_path, shots, manifest.fps)
                pose_tracker.unload_model()
            total_persons = sum(len(v) for v in poses.values())
            progress.update(task, description=f"[green]骨架[/green]: {len(poses)} 鏡頭中偵測到 {total_persons} 人")
            progress.remove_task(task)

        # ── Layer 2: 結構組裝 ──
        task = progress.add_task("組裝時間軸...", total=None)
        shot_data = align_timeline(shots, camera_motions, poses, audio_features)
        shot_data = enrich_shots(shot_data, video_path, manifest.fps)
        progress.update(task, description="[green]時間軸已組裝[/green]")
        progress.remove_task(task)

        # ── Layer 3: 導演指紋 ──
        task = progress.add_task("計算導演風格指紋...", total=None)
        fingerprint = compute_fingerprint(shot_data, manifest.duration_sec)
        pacing_zh = zh(PACING_ZH, fingerprint.pacing)
        progress.update(task, description=f"[green]風格指紋[/green]: {pacing_zh}節奏, {fingerprint.cuts_per_minute:.1f} 剪/分鐘")
        progress.remove_task(task)

        # ── 主體錨定 ──
        task = progress.add_task("選取關鍵幀...", total=None)
        keyframes = select_keyframes(video_path, shots, cfg.output_dir)
        progress.update(task, description=f"[green]關鍵幀[/green]: 已選取 {sum(len(v) for v in keyframes.values())} 張")
        progress.remove_task(task)

        for sd in shot_data:
            sd.keyframe_paths = keyframes.get(sd.shot_index, [])

        subject_cards = []
        ref_map = {}

        # ── Layer 4: Prompt 生成 ──
        prompts = []
        if not no_prompts:
            task = progress.add_task("透過 Claude API 生成 Prompt...", total=None)
            prompts = generate_prompts(shot_data, keyframes)
            progress.update(task, description=f"[green]Prompt[/green]: 已生成 {len(prompts)} 組")
            progress.remove_task(task)

    # ── 輸出 ──
    analysis = VideoAnalysis(
        metadata=metadata,
        shots=shot_data,
        audio_features=audio_features,
        fingerprint=fingerprint,
        prompts=prompts,
        subject_cards=subject_cards if 'subject_cards' in dir() else [],
    )

    output_path = cfg.output_dir / f"{video_path.stem}_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(analysis.model_dump_json(indent=2))

    pacing_zh = zh(PACING_ZH, fingerprint.pacing)
    console.print(f"\n[bold green]分析完成！[/bold green]")
    console.print(f"  輸出檔案: [cyan]{output_path}[/cyan]")
    console.print(f"  鏡頭數量: {len(shot_data)}")
    console.print(f"  Prompt 數: {len(prompts)}")
    console.print(f"  主體身份卡: {len(subject_cards) if 'subject_cards' in dir() else 0}")
    console.print(f"  風格指紋: {pacing_zh} ({fingerprint.cuts_per_minute:.1f} 剪/分鐘)")


@main.command()
@click.argument("json_path", type=click.Path(exists=True))
def inspect(json_path: str):
    """檢視分析結果 JSON 檔案。"""
    from director.structure.schema import VideoAnalysis

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    analysis = VideoAnalysis(**data)

    console.print(f"\n[bold]影片:[/bold] {analysis.metadata.filename}")
    console.print(f"  時長: {analysis.metadata.duration_sec:.1f}秒 | 幀率: {analysis.metadata.fps}")
    console.print(f"  解析度: {analysis.metadata.width}x{analysis.metadata.height}")

    console.print(f"\n[bold]鏡頭:[/bold] 共 {len(analysis.shots)} 個")
    for shot in analysis.shots[:10]:
        cam = zh(CAMERA_ZH, shot.camera_motion.type)
        size = zh(SHOT_SIZE_ZH, shot.composition.shot_size)
        trans = zh(TRANSITION_ZH, shot.transition_in)
        console.print(f"  [{shot.shot_index:3d}] {shot.timecode_start}-{shot.timecode_end} "
                      f"({shot.duration_sec:.1f}秒) | {size} | {cam} | {trans}")

    if len(analysis.shots) > 10:
        console.print(f"  ... 還有 {len(analysis.shots) - 10} 個鏡頭")

    fp = analysis.fingerprint
    pacing_zh = zh(PACING_ZH, fp.pacing)
    console.print(f"\n[bold]導演風格指紋:[/bold]")
    console.print(f"  節奏: {pacing_zh} | 剪輯率: {fp.cuts_per_minute} 剪/分鐘")
    console.print(f"  平均鏡頭: {fp.avg_shot_duration:.2f}秒 | 韻律: {fp.rhythm_pattern}")
    console.print(f"  常用景別: {', '.join(zh(SHOT_SIZE_ZH, s) for s in fp.dominant_shot_sizes)}")
    console.print(f"  招牌運鏡: {', '.join(zh(CAMERA_ZH, m) for m in fp.signature_camera_moves) or '無'}")

    if analysis.prompts:
        console.print(f"\n[bold]AI 生成 Prompt:[/bold] 共 {len(analysis.prompts)} 組")
        p = analysis.prompts[0]
        console.print(f"  [鏡頭 0] {p.scene_description[:100]}...")


@main.command()
@click.argument("video_paths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="輸出目錄")
@click.option("--no-prompts", is_flag=True, help="跳過 AI Prompt 生成")
@click.option("--verbose", "-v", is_flag=True, help="詳細日誌")
def batch(video_paths: tuple[str, ...], output_dir: str | None, no_prompts: bool, verbose: bool):
    """批次分析多支影片。

    用法: director batch video1.mp4 video2.mp4 video3.mp4
    """
    setup_logging(verbose)
    from click import Context

    console.print(f"\n[bold]批次分析[/bold] — 共 {len(video_paths)} 支影片\n")

    for i, vp in enumerate(video_paths, 1):
        console.print(f"\n[bold cyan]── [{i}/{len(video_paths)}] {Path(vp).name} ──[/bold cyan]")
        ctx = Context(analyze)
        ctx.invoke(
            analyze,
            video_path=vp,
            output_dir=output_dir,
            skip_pose=False,
            skip_audio=False,
            skip_camera=False,
            no_prompts=no_prompts,
            verbose=verbose,
        )

    console.print(f"\n[bold green]批次完成！[/bold green] 共處理 {len(video_paths)} 支影片")


@main.command()
@click.argument("json_path", type=click.Path(exists=True))
@click.option("--shot", "-s", type=int, default=None, help="只顯示指定鏡頭編號的詳細資訊")
@click.option("--prompts", "-p", is_flag=True, help="顯示所有 Prompt 內容")
def report(json_path: str, shot: int | None, prompts: bool):
    """產出中文摘要報告。"""
    from director.structure.schema import VideoAnalysis

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    analysis = VideoAnalysis(**data)
    fp = analysis.fingerprint

    if shot is not None:
        # ── 單鏡詳情 ──
        target = next((s for s in analysis.shots if s.shot_index == shot), None)
        if not target:
            console.print(f"[red]找不到鏡頭 #{shot}[/red]")
            return

        console.print(f"\n[bold]鏡頭 #{shot} 詳細分析[/bold]")
        console.print(f"  時間碼: {target.timecode_start} → {target.timecode_end} ({target.duration_sec:.2f}秒)")
        console.print(f"  景別: {zh(SHOT_SIZE_ZH, target.composition.shot_size)}")
        console.print(f"  攝影機角度: {target.composition.angle}")
        console.print(f"  景深層數: {target.composition.depth_layers}")
        console.print(f"  三分法分數: {target.composition.rule_of_thirds_score}")

        console.print(f"\n  [bold]攝影機運動:[/bold]")
        cam = target.camera_motion
        console.print(f"    類型: {zh(CAMERA_ZH, cam.type)}")
        console.print(f"    強度: {cam.intensity}")
        console.print(f"    方向: {cam.dominant_direction}")
        console.print(f"    平均光流: {cam.avg_flow_magnitude}")

        console.print(f"\n  [bold]轉場:[/bold]")
        console.print(f"    入: {zh(TRANSITION_ZH, target.transition_in)}")
        console.print(f"    出: {zh(TRANSITION_ZH, target.transition_out)}")

        console.print(f"\n  [bold]色彩:[/bold]")
        console.print(f"    主色調: {', '.join(target.color.dominant_palette[:5])}")
        console.print(f"    亮度: {target.color.avg_brightness} | 對比度: {target.color.contrast_ratio}")
        console.print(f"    色溫: {target.color.color_temp_k}K")

        if target.characters:
            console.print(f"\n  [bold]人物:[/bold] {len(target.characters)} 人")
            for c in target.characters:
                console.print(f"    #{c.track_id}: {c.action_tag} @ {c.screen_position}")

        console.print(f"\n  [bold]音頻同步:[/bold]")
        console.print(f"    能量: {target.audio_sync.energy_level}")
        console.print(f"    踩拍切割: {'是' if target.audio_sync.is_on_beat_cut else '否'}")
        console.print(f"    拍點數: {len(target.audio_sync.beat_positions)}")

        # Show prompt if available
        prompt = next((p for p in analysis.prompts if p.shot_index == shot), None)
        if prompt:
            console.print(f"\n  [bold]AI Prompt:[/bold]")
            console.print(f"    場景: {prompt.scene_description}")
            console.print(f"    Seedance: {prompt.seedance_prompt}")
            console.print(f"    Kling: {prompt.kling_prompt}")
            console.print(f"    Negative: {prompt.negative_prompt}")
        return

    # ── 完整摘要報告 ──
    pacing_zh = zh(PACING_ZH, fp.pacing)

    console.print(f"\n{'='*60}")
    console.print(f"[bold]影片分析摘要報告[/bold]")
    console.print(f"{'='*60}")

    console.print(f"\n[bold]基本資訊[/bold]")
    console.print(f"  檔案: {analysis.metadata.filename}")
    console.print(f"  時長: {analysis.metadata.duration_sec:.1f}秒 ({analysis.metadata.duration_sec/60:.1f}分鐘)")
    console.print(f"  解析度: {analysis.metadata.width}x{analysis.metadata.height} @ {analysis.metadata.fps}fps")

    console.print(f"\n[bold]剪輯結構[/bold]")
    console.print(f"  總鏡頭數: {fp.total_shots}")
    console.print(f"  剪輯率: {fp.cuts_per_minute} 剪/分鐘")
    console.print(f"  平均鏡頭: {fp.avg_shot_duration:.2f}秒 (中位數: {fp.median_shot_duration:.2f}秒)")
    console.print(f"  時長標準差: {fp.shot_duration_std:.2f}秒")

    console.print(f"\n[bold]風格指紋[/bold]")
    console.print(f"  節奏: {pacing_zh}")
    console.print(f"  韻律: {fp.rhythm_pattern}")
    console.print(f"  常用景別: {', '.join(zh(SHOT_SIZE_ZH, s) for s in fp.dominant_shot_sizes)}")
    console.print(f"  招牌運鏡: {', '.join(zh(CAMERA_ZH, m) for m in fp.signature_camera_moves) or '無'}")

    if fp.shot_size_distribution:
        console.print(f"\n[bold]景別分布[/bold]")
        for size, count in sorted(fp.shot_size_distribution.items(), key=lambda x: -x[1]):
            bar = "█" * int(count / max(fp.shot_size_distribution.values()) * 20)
            console.print(f"  {zh(SHOT_SIZE_ZH, size):>6} {bar} {count}")

    if fp.camera_motion_distribution:
        console.print(f"\n[bold]運鏡分布[/bold]")
        for motion, count in sorted(fp.camera_motion_distribution.items(), key=lambda x: -x[1]):
            bar = "█" * int(count / max(fp.camera_motion_distribution.values()) * 20)
            console.print(f"  {zh(CAMERA_ZH, motion):>6} {bar} {count}")

    if fp.transition_distribution:
        console.print(f"\n[bold]轉場分布[/bold]")
        for trans, count in sorted(fp.transition_distribution.items(), key=lambda x: -x[1]):
            bar = "█" * int(count / max(fp.transition_distribution.values()) * 20)
            console.print(f"  {zh(TRANSITION_ZH, trans):>6} {bar} {count}")

    if fp.color_fingerprint:
        console.print(f"\n[bold]色彩指紋[/bold]")
        console.print(f"  {' '.join(fp.color_fingerprint[:8])}")

    if analysis.audio_features.bpm > 0:
        af = analysis.audio_features
        console.print(f"\n[bold]音頻特徵[/bold]")
        console.print(f"  BPM: {af.bpm}")
        console.print(f"  拍點數: {len(af.beat_timestamps)}")
        console.print(f"  Onset 數: {len(af.onset_timestamps)}")
        console.print(f"  平均能量: {af.avg_energy}")

    if prompts and analysis.prompts:
        console.print(f"\n[bold]AI 生成 Prompt[/bold] (共 {len(analysis.prompts)} 組)")
        for p in analysis.prompts:
            console.print(f"\n  [bold]鏡頭 #{p.shot_index}[/bold] ({p.duration_hint:.1f}秒)")
            console.print(f"  場景: {p.scene_description}")
            console.print(f"  Seedance: {p.seedance_prompt}")
            console.print(f"  Kling: {p.kling_prompt}")

    console.print(f"\n{'='*60}")


@main.command()
@click.option("--project", "-p", default="", help="專案 ID")
@click.option("--csv", type=click.Path(), default=None, help="匯出 CSV 路徑")
def cost(project: str, csv: str | None):
    """查看 API 使用量和費用統計。"""
    from director.utils.cost_tracker import get_tracker

    tracker = get_tracker()
    if project:
        tracker.set_project(project)

    summary = tracker.get_project_summary(project or None)

    console.print(f"\n{'='*50}")
    console.print(f"[bold]API 費用統計[/bold] — {summary['project_id']}")
    console.print(f"{'='*50}")

    c = summary["claude"]
    console.print(f"\n[bold]Claude API[/bold]")
    console.print(f"  呼叫次數: {c['calls']}")
    console.print(f"  Input tokens: {c['input_tokens']:,}")
    console.print(f"  Output tokens: {c['output_tokens']:,}")
    console.print(f"  Cached tokens: {c['cached_tokens']:,}")
    console.print(f"  總 tokens: {c['total_tokens']:,}")
    console.print(f"  預估費用: [yellow]${c['estimated_cost_usd']:.4f}[/yellow]")

    h = summary["higgsfield"]
    console.print(f"\n[bold]Higgsfield API[/bold]")
    console.print(f"  呼叫次數: {h['calls']}")
    console.print(f"  總時長: {h['total_duration_sec']}s")
    console.print(f"  預估費用: [yellow]${h['estimated_cost_usd']:.4f}[/yellow]")

    console.print(f"\n[bold green]總費用: ${summary['total_estimated_cost_usd']:.4f}[/bold green]")

    if csv:
        path = tracker.export_csv(csv, project or None)
        console.print(f"\n已匯出 CSV: [cyan]{path}[/cyan]")


if __name__ == "__main__":
    main()
