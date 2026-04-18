"""Claude API Vision: keyframe analysis → scene descriptions + Seedance/Kling prompts."""

from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path

from director.config import get_config
from director.structure.schema import GenerationPrompt, ShotData

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位專業的影片導演兼攝影指導，正在分析參考影片素材來產生 AI 影片生成 Prompt。

## 你的任務
根據提供的鏡頭結構化數據和關鍵幀圖片，為每個鏡頭產生三種格式的 Prompt。

## 輸出格式（嚴格 JSON）
```json
{
  "scene_description": "自然語言場景描述（英文，50-80字）",
  "seedance_prompt": "Seedance 格式 Prompt（英文）",
  "kling_prompt": "Kling 格式 Prompt（英文）",
  "negative_prompt": "負面提示詞（英文）"
}
```

## Seedance Prompt 結構
格式：`[Subject] [performing Action], [Camera movement], in [Environment/Scene], [Visual Style], [Lighting], [Color mood]`
- Subject 要具體（不要只寫 "a person"，要描述外觀特徵）
- Action 要有動態感，用進行式
- Camera 要精確（tracking shot, dolly zoom, crane up, steadicam follow, etc.）
- 如果鏡頭 > 3 秒，拆成 2-3 個時間段：`[0s-2s] ... [2s-4s] ...`

## Kling Prompt 結構
四段式，句號分隔：
`[Scene setting with atmosphere]. [Subject with detailed appearance]. [Motion and camera movement]. [Visual style, color grading, and mood].`

## 品質要求
1. 從關鍵幀圖片中提取：人物外觀、服裝、場景細節、光線方向、色調
2. 結合結構化數據：攝影機運動類型、景別、色彩數值、音頻節奏
3. 具體而非抽象：用 "warm golden hour backlight with lens flare" 而不是 "nice lighting"
4. Negative prompt 要針對性地避免該鏡頭可能出現的問題

## 重要
- 全部用英文撰寫 Prompt
- 每個 prompt < 200 字
- 直接回傳 JSON，不要加任何說明文字"""

FEW_SHOT_EXAMPLE = """範例輸入：
- 景別：medium_close_up
- 攝影機：handheld_push_in, intensity 0.7
- 色彩：dominant #1a3a4a (深藍綠), brightness 0.4
- 音頻：energy 0.85, on-beat cut

範例輸出：
```json
{
  "scene_description": "A tense medium close-up of a man in a dark tactical vest, handheld camera pushing in with urgency. Cool teal lighting bathes the scene as the cut lands precisely on a heavy bass beat, creating visceral rhythm.",
  "seedance_prompt": "A rugged man in dark tactical gear, gripping a weapon and scanning the environment with intense focus, handheld camera pushing in with deliberate urgency, in a dimly lit industrial corridor with teal emergency lighting casting harsh shadows, gritty cinematic style with anamorphic lens distortion, cool desaturated color palette with teal and dark navy tones",
  "kling_prompt": "Dark industrial corridor bathed in cold teal emergency lighting with visible atmospheric haze. A focused man in tactical vest and gear, positioned slightly off-center in medium close-up, with determined expression and coiled tension. Handheld camera pushes in with controlled intensity, slight natural shake adding urgency to the movement. Gritty cinematic look with desaturated cool tones, high contrast shadows, and anamorphic bokeh.",
  "negative_prompt": "steady tripod shot, bright cheerful lighting, warm colors, clean environments, casual clothing, smiling, smooth dolly movement, overexposed"
}
```"""


def generate_prompts(
    shots: list[ShotData],
    keyframes: dict[int, list[str]],
) -> list[GenerationPrompt]:
    """Generate AI video prompts for all shots using Claude Vision API."""
    cfg = get_config()
    prompts = []

    try:
        import anthropic
        client = anthropic.Anthropic()
    except Exception as e:
        log.error("Cannot initialize Anthropic client: %s", e)
        log.info("Set ANTHROPIC_API_KEY to enable prompt generation.")
        return [_fallback_prompt(shot) for shot in shots]

    for i in range(0, len(shots), cfg.claude_batch_size):
        batch = shots[i : i + cfg.claude_batch_size]
        for shot in batch:
            kf_paths = keyframes.get(shot.shot_index, [])
            prompt = _generate_single_prompt(client, shot, kf_paths, cfg)
            prompts.append(prompt)

        if i + cfg.claude_batch_size < len(shots):
            time.sleep(cfg.claude_batch_delay)

    log.info("Generated %d prompts", len(prompts))
    return prompts


def _generate_single_prompt(client, shot: ShotData, keyframe_paths: list[str], cfg) -> GenerationPrompt:
    """Generate prompt for a single shot with structured context."""
    content = []

    # Add keyframe images (with validation)
    for kf_path in keyframe_paths[:3]:
        try:
            p = Path(kf_path)
            if not p.exists():
                log.warning("Keyframe not found: %s", kf_path)
                continue
            file_size = p.stat().st_size
            if file_size == 0:
                log.warning("Keyframe is empty (0 bytes): %s", kf_path)
                continue
            raw = p.read_bytes()
            # Validate JPEG header (SOI marker)
            if len(raw) < 2 or raw[0] != 0xFF or raw[1] != 0xD8:
                log.warning("Keyframe is not a valid JPEG: %s", kf_path)
                continue
            # Resize if too large for API (max ~20MB base64 ≈ ~15MB raw)
            if file_size > 10 * 1024 * 1024:
                log.info("Keyframe too large (%d MB), re-encoding: %s", file_size // (1024*1024), kf_path)
                import cv2
                img = cv2.imread(str(p))
                if img is None:
                    log.warning("cv2 cannot decode keyframe: %s", kf_path)
                    continue
                _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
                raw = buf.tobytes()
            img_data = base64.b64encode(raw).decode("utf-8")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": img_data},
            })
        except Exception as e:
            log.warning("Cannot read keyframe %s: %s", kf_path, e)

    # Build structured context with precise quantitative data
    comp = shot.composition
    cam = shot.camera_motion
    col = shot.color
    layout = comp.subject_layout

    context_parts = [
        f"## 鏡頭 #{shot.shot_index}  ({shot.duration_sec:.1f}s)",
        f"",
        f"### 攝影機",
        f"- 運動: {cam.type} (強度: {cam.intensity})",
        f"- 轉場: {shot.transition_in} → {shot.transition_out}",
    ]
    if cam.yaw_deg or cam.pitch_deg:
        context_parts.append(f"- Homography: yaw={cam.yaw_deg}°, pitch={cam.pitch_deg}°, roll={cam.roll_deg}°")

    context_parts += [
        f"",
        f"### 構圖",
        f"- 景別: {comp.shot_size} (主體高度佔比: {comp.shot_size_ratio:.1%})",
        f"- 視覺重心: ({comp.visual_weight_x:.2f}, {comp.visual_weight_y:.2f})",
        f"- 三分法分數: {comp.rule_of_thirds_score:.2f}",
    ]
    if comp.thirds_grid:
        grid = comp.thirds_grid
        context_parts.append(f"- 九宮格主體分布: TL={grid[0]:.0%} TC={grid[1]:.0%} TR={grid[2]:.0%} / ML={grid[3]:.0%} MC={grid[4]:.0%} MR={grid[5]:.0%} / BL={grid[6]:.0%} BC={grid[7]:.0%} BR={grid[8]:.0%}")

    if layout.total_subjects > 0:
        context_parts += [
            f"- 主體數量: {layout.total_subjects}",
            f"- 主體總佔比: {layout.total_coverage:.1%}, 背景: {layout.background_ratio:.1%}",
            f"- 主體質心: ({layout.centroid_x:.2f}, {layout.centroid_y:.2f})",
            f"- 分散度: {layout.spread:.2f}, 對稱度: {layout.symmetry_score:.2f}",
        ]

    if shot.characters:
        context_parts.append(f"")
        context_parts.append(f"### 人物")
        for c in shot.characters:
            context_parts.append(
                f"- #{c.track_id}: {c.action_tag} @ 位置({c.center_x:.2f}, {c.center_y:.2f}), "
                f"佔畫面{c.frame_coverage:.1%}, "
                f"headroom={c.headroom:.1%}, "
                f"lead_L={c.lead_room_left:.1%}/R={c.lead_room_right:.1%}, "
                f"三分法點={c.nearest_thirds_point}(距離{c.thirds_distance:.2f})"
            )

    context_parts += [
        f"",
        f"### 色彩",
    ]
    if col.palette_detailed:
        for ce in col.palette_detailed[:4]:
            context_parts.append(
                f"- {ce.hex} ({ce.name}) — 佔{ce.weight:.0%}, HSL({ce.hsl[0]:.0f}°, {ce.hsl[1]:.0f}%, {ce.hsl[2]:.0f}%)"
            )
    context_parts += [
        f"- 亮度: {col.avg_brightness:.2f}, 飽和度: {col.avg_saturation:.2f}, 對比: {col.contrast_ratio:.2f}",
        f"- 色溫: {col.color_temp_k}K, 主色相: {col.dominant_hue:.0f}°",
        f"- 暖色: {col.warm_ratio:.0%} / 冷色: {col.cool_ratio:.0%} / 中性: {col.neutral_ratio:.0%}",
        f"- 暗部: {col.shadow_ratio:.0%} / 中間調: {col.midtone_ratio:.0%} / 亮部: {col.highlight_ratio:.0%}",
        f"",
        f"### 音頻",
        f"- 能量: {shot.audio_sync.energy_level}, 踩拍: {'是' if shot.audio_sync.is_on_beat_cut else '否'}",
    ]

    # Add text ignore instruction
    from director.perception.text_filter import get_text_ignore_instruction
    context_parts.append(get_text_ignore_instruction())

    context_text = "\n".join(context_parts)

    content.append({
        "type": "text",
        "text": f"請分析以下鏡頭並產生 AI 影片生成 Prompt：\n\n{context_text}\n\n{FEW_SHOT_EXAMPLE}\n\n請直接回傳 JSON。",
    })

    try:
        response = client.messages.create(
            model=cfg.claude_model,
            max_tokens=cfg.claude_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )

        # Track cost
        try:
            from director.utils.cost_tracker import get_tracker
            usage = response.usage
            get_tracker().track_claude(
                model=cfg.claude_model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_tokens=getattr(usage, "cache_read_input_tokens", 0),
                shot_index=shot.shot_index,
                description=f"prompt_gen_shot_{shot.shot_index}",
            )
        except Exception:
            pass

        text = response.content[0].text

        # Extract JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        # Try to parse, handle potential formatting issues
        text = text.strip()
        data = json.loads(text)

        return GenerationPrompt(
            shot_index=shot.shot_index,
            scene_description=data.get("scene_description", ""),
            seedance_prompt=data.get("seedance_prompt", ""),
            kling_prompt=data.get("kling_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            duration_hint=shot.duration_sec,
        )
    except json.JSONDecodeError as e:
        log.warning("JSON parse failed for shot %d: %s — raw: %s", shot.shot_index, e, text[:200])
        return _fallback_prompt(shot)
    except Exception as e:
        log.warning("Claude API failed for shot %d: %s", shot.shot_index, e)
        return _fallback_prompt(shot)


def _fallback_prompt(shot: ShotData) -> GenerationPrompt:
    """Generate a basic prompt without Claude API."""
    cam = shot.camera_motion
    cam_str = cam.type.replace("_", " ")
    size_str = shot.composition.shot_size.replace("_", " ")

    # Build more descriptive fallback
    color_desc = ""
    if shot.color.dominant_palette:
        color_desc = f", {_describe_color_mood(shot.color.dominant_palette[0])} color palette"

    seedance = (
        f"A cinematic scene, "
        f"{'static camera' if cam.type == 'static' else cam_str + ' camera movement'}, "
        f"{size_str} framing{color_desc}, "
        f"professional cinematography with natural lighting"
    )

    kling = (
        f"Cinematic environment with atmospheric lighting. "
        f"Subject framed in {size_str}. "
        f"{'Camera holds steady' if cam.type == 'static' else 'Camera ' + cam_str + ' with controlled pace'}. "
        f"Professional film look with subtle color grading{color_desc}."
    )

    return GenerationPrompt(
        shot_index=shot.shot_index,
        scene_description=f"Shot {shot.shot_index}: {size_str} with {cam_str} camera",
        seedance_prompt=seedance,
        kling_prompt=kling,
        negative_prompt="blurry, low quality, distorted, watermark, overexposed, underexposed, shaky",
        duration_hint=shot.duration_sec,
    )


def _describe_color_mood(hex_color: str) -> str:
    """Convert a hex color to a mood descriptor."""
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    except (ValueError, IndexError):
        return "neutral"

    brightness = (r + g + b) / 3 / 255

    if brightness < 0.2:
        return "dark and moody"
    elif brightness > 0.8:
        return "bright and airy"
    elif r > b * 1.5 and r > g:
        return "warm"
    elif b > r * 1.5:
        return "cool"
    elif g > r and g > b:
        return "natural green"
    else:
        return "neutral"
