"""Sound Spotting List — 為每個鏡頭產出 foley / SFX / music 建議清單。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FoleyEvent:
    time_offset: float   # 鏡頭內時間
    event_type: str      # "footstep", "bottle_place", "fabric_rustle" etc.
    intensity: str       # "soft", "medium", "sharp"


@dataclass
class SFXSuggestion:
    time_offset: float
    sfx_type: str        # "whoosh_in", "impact", "rise", "bass_drop"
    duration: float


@dataclass
class SoundSpottingEntry:
    shot_index: int
    duration_sec: float
    narrative_section: str   # intro / verse / build / drop / outro
    music_energy: str        # "low", "medium", "high"

    foley_events: list[FoleyEvent] = field(default_factory=list)
    sfx_suggestions: list[SFXSuggestion] = field(default_factory=list)
    notes: str = ""


# 鏡頭用途 → Foley 事件對應
PURPOSE_FOLEY_MAP: dict[str, list[dict]] = {
    "環境建立": [
        {"type": "ambient_room_tone", "intensity": "soft", "offset": 0},
    ],
    "商品展示": [
        {"type": "bottle_place", "intensity": "sharp", "offset": 0.3},
        {"type": "subtle_movement", "intensity": "soft", "offset": 0.8},
    ],
    "人物使用": [
        {"type": "fabric_rustle", "intensity": "soft", "offset": 0.2},
        {"type": "product_interaction", "intensity": "medium", "offset": 0.5},
    ],
    "功能演示": [
        {"type": "product_action", "intensity": "medium", "offset": 0.4},
        {"type": "reveal_impact", "intensity": "sharp", "offset": 1.2},
    ],
    "情緒感受": [
        {"type": "breath", "intensity": "soft", "offset": 0.3},
        {"type": "heartbeat_optional", "intensity": "soft", "offset": 0.8},
    ],
    "質感特寫": [
        {"type": "micro_texture", "intensity": "soft", "offset": 0.2},
    ],
    "品牌資訊": [
        {"type": "logo_reveal", "intensity": "medium", "offset": 0.5},
    ],
    "轉場過渡": [
        {"type": "whoosh_transition", "intensity": "medium", "offset": 0},
    ],
    "蒙太奇": [
        {"type": "rhythmic_hit", "intensity": "sharp", "offset": 0},
    ],
}


# 音樂段落 → SFX 建議
SECTION_SFX_MAP: dict[str, list[dict]] = {
    "intro": [
        {"type": "ambient_fade_in", "duration": 0.5, "offset": 0},
    ],
    "verse": [],
    "build": [
        {"type": "tension_rise", "duration": 1.0, "offset": 0},
    ],
    "drop": [
        {"type": "bass_drop", "duration": 0.3, "offset": 0},
        {"type": "impact_hit", "duration": 0.2, "offset": 0.1},
    ],
    "outro": [
        {"type": "fade_out_ambient", "duration": 1.0, "offset": 0},
    ],
}


def generate_spotting_list(
    shots: list[dict],
    music_sections: list | None = None,
) -> list[SoundSpottingEntry]:
    """為鏡頭表產出 Sound Spotting List。

    shots: list of {"shot_index", "duration_sec", "purpose", "start_sec"}
    music_sections: list of MusicSection
    """
    entries = []

    for shot in shots:
        idx = shot.get("shot_index", -1)
        dur = shot.get("duration_sec", 3.0)
        purpose = shot.get("purpose", "環境建立")
        start_sec = shot.get("start_sec", 0)

        # Determine music section
        section = "verse"
        energy = "medium"
        if music_sections:
            for s in music_sections:
                s_start = s.get("start_sec", 0) if isinstance(s, dict) else s.start_sec
                s_end = s.get("end_sec", 0) if isinstance(s, dict) else s.end_sec
                s_name = s.get("name", "") if isinstance(s, dict) else s.name
                s_energy = s.get("avg_energy", 0.5) if isinstance(s, dict) else s.avg_energy
                if s_start <= start_sec < s_end:
                    section = s_name
                    energy = "high" if s_energy > 0.6 else "medium" if s_energy > 0.3 else "low"
                    break

        # Foley events based on purpose
        foley_events = []
        for fol in PURPOSE_FOLEY_MAP.get(purpose, []):
            offset = fol["offset"]
            if offset < dur:
                foley_events.append(FoleyEvent(
                    time_offset=offset, event_type=fol["type"], intensity=fol["intensity"]
                ))

        # SFX based on music section
        sfx_list = []
        for sfx in SECTION_SFX_MAP.get(section, []):
            sfx_list.append(SFXSuggestion(
                time_offset=sfx["offset"], sfx_type=sfx["type"], duration=sfx["duration"]
            ))

        entries.append(SoundSpottingEntry(
            shot_index=idx,
            duration_sec=dur,
            narrative_section=section,
            music_energy=energy,
            foley_events=foley_events,
            sfx_suggestions=sfx_list,
        ))

    return entries


def export_spotting_csv(entries: list[SoundSpottingEntry], output_path: str) -> str:
    """匯出 Sound Spotting List 成 CSV 給音效師。"""
    lines = ["Shot,Duration,Section,Energy,Foley,SFX,Notes"]
    for e in entries:
        foley_str = "; ".join(f"{f.event_type}@{f.time_offset:.1f}s ({f.intensity})" for f in e.foley_events)
        sfx_str = "; ".join(f"{s.sfx_type}@{s.time_offset:.1f}s ({s.duration:.1f}s)" for s in e.sfx_suggestions)
        lines.append(f"S-{e.shot_index:02d},{e.duration_sec:.1f},{e.narrative_section},{e.music_energy},\"{foley_str}\",\"{sfx_str}\",\"{e.notes}\"")

    from pathlib import Path
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return output_path
