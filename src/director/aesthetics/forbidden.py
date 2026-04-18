"""AI 禁區偵測 — 掃描 prompt / shot description 找出 AI 容易崩的場景。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ForbiddenZone:
    zone_type: str
    risk_score: int  # 1-10
    matched_keywords: list[str]
    suggestion: str


FORBIDDEN_RULES: dict[str, dict] = {
    "文字_中文": {
        "keywords": ["中文字", "漢字", "字幕", "招牌", "標語", "書法", "chinese text", "subtitle"],
        "risk": 10,
        "suggestion": "改為「blank label, add text in post-production」，文字請後製疊加",
    },
    "文字_英文": {
        "keywords": ["logo text", "brand name", "billboard", "sign with text", "license plate"],
        "risk": 8,
        "suggestion": "改為「abstract text shapes, no readable text」，精確文字後製處理",
    },
    "Logo_特寫": {
        "keywords": ["logo close-up", "brand logo", "logo detail", "macro logo"],
        "risk": 10,
        "suggestion": "改為生成商品但 logo 區域模糊，後製疊加真實 logo",
    },
    "手指_小物件": {
        "keywords": ["holding", "grip", "手拿", "握", "pinch", "finger", "手指"],
        "risk": 7,
        "suggestion": "改為廣角手部或物件平放在桌面，避免手指特寫",
    },
    "液體_倒出": {
        "keywords": ["pouring", "倒", "splash", "flowing liquid", "pour out"],
        "risk": 8,
        "suggestion": "改為液體已在容器中的靜態畫面，或液滴落下瞬間（較穩）",
    },
    "多人_擁抱": {
        "keywords": ["hug", "embrace", "擁抱", "交纏", "intertwined", "holding hands"],
        "risk": 6,
        "suggestion": "改為並排構圖，避免肢體交纏導致 AI 崩",
    },
    "鏡面_完美反射": {
        "keywords": ["mirror reflection", "perfect reflection", "鏡面", "完美反射"],
        "risk": 5,
        "suggestion": "加入景深 bokeh 或輕微失焦的反射",
    },
    "對稱_物件": {
        "keywords": ["perfectly symmetrical", "完全對稱", "identical twins"],
        "risk": 4,
        "suggestion": "引入輕微不對稱元素避免 uncanny",
    },
    "眼睛_特寫": {
        "keywords": ["eye close-up", "眼睛特寫", "iris detail", "extreme eye"],
        "risk": 7,
        "suggestion": "改為半臉或眼周柔焦特寫，避免虹膜細節崩壞",
    },
    "牙齒_笑": {
        "keywords": ["teeth", "grin", "露齒", "smile showing teeth"],
        "risk": 6,
        "suggestion": "微笑但嘴型閉合，或側臉微笑避免牙齒細節",
    },
}


def detect_forbidden_zones(text: str) -> list[ForbiddenZone]:
    """掃描文字找出 AI 禁區。"""
    text_lower = text.lower()
    results = []

    for zone_name, rule in FORBIDDEN_RULES.items():
        matched = [kw for kw in rule["keywords"] if kw.lower() in text_lower]
        if matched:
            results.append(ForbiddenZone(
                zone_type=zone_name,
                risk_score=rule["risk"],
                matched_keywords=matched,
                suggestion=rule["suggestion"],
            ))

    # 按風險排序
    results.sort(key=lambda x: -x.risk_score)
    return results


def auto_rewrite_forbidden(prompt: str, zones: list[ForbiddenZone]) -> str:
    """根據偵測到的禁區，自動重寫 prompt。"""
    if not zones:
        return prompt

    suffix_notes = []
    for z in zones:
        if z.risk_score >= 7:
            suffix_notes.append(f"[AVOID {z.zone_type}: {z.suggestion}]")

    if suffix_notes:
        return prompt + " " + " ".join(suffix_notes)
    return prompt
