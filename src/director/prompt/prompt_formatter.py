"""Format prompts for specific AI video generators (Seedance, Kling)."""

from __future__ import annotations

from director.structure.schema import GenerationPrompt


def format_for_seedance(prompt: GenerationPrompt) -> str:
    """Format prompt for Seedance timeline prompting.

    For shots > 3s, split into temporal segments.
    """
    base = prompt.seedance_prompt
    if not base:
        return ""

    duration = prompt.duration_hint
    if duration <= 3.0:
        return base

    # Split into 2-3 segments for timeline prompting
    segments = []
    seg_count = min(3, max(2, int(duration / 2)))
    seg_dur = duration / seg_count

    for i in range(seg_count):
        start = round(i * seg_dur, 1)
        end = round((i + 1) * seg_dur, 1)
        segments.append(f"[{start}s-{end}s] {base}")

    return "\n".join(segments)


def format_for_kling(prompt: GenerationPrompt) -> str:
    """Format prompt for Kling four-area format."""
    return prompt.kling_prompt or ""


def format_all_prompts(prompts: list[GenerationPrompt]) -> dict:
    """Format all prompts into a structured output dict."""
    return {
        "shots": [
            {
                "shot_index": p.shot_index,
                "duration_hint": p.duration_hint,
                "scene_description": p.scene_description,
                "seedance": format_for_seedance(p),
                "kling": format_for_kling(p),
                "negative": p.negative_prompt,
            }
            for p in prompts
        ]
    }
