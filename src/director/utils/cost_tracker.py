"""Token & cost tracking for Claude API + Higgsfield API.

每次 API 呼叫都記錄：timestamp, model, tokens, estimated cost.
支援 per-project 統計、匯出 JSON/CSV、即時查詢。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock

log = logging.getLogger(__name__)

# ── Pricing (2026-04 estimates) ──

CLAUDE_PRICING = {
    # model_id: (input_per_1M_tokens, output_per_1M_tokens) in USD
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-opus-4-20250514": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    # Fallback
    "default": (3.0, 15.0),
}

HIGGSFIELD_PRICING = {
    # resolution: cost_per_second in USD (estimate)
    "480p": 0.02,
    "720p": 0.04,
    "1080p": 0.08,
    "default": 0.04,
}


@dataclass
class APICall:
    timestamp: str
    service: str          # "claude" or "higgsfield"
    model: str
    project_id: str = ""

    # Claude-specific
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    # Higgsfield-specific
    duration_sec: float = 0
    resolution: str = ""
    generation_id: str = ""

    # Cost
    estimated_cost_usd: float = 0.0

    # Metadata
    shot_index: int = -1
    description: str = ""


class CostTracker:
    """Track API usage and costs per project."""

    def __init__(self, storage_dir: str | Path | None = None):
        self._calls: list[APICall] = []
        self._lock = Lock()
        self._storage_dir = Path(storage_dir) if storage_dir else None
        self._current_project: str = ""

        if self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def set_project(self, project_id: str):
        """Set current project for tagging."""
        self._current_project = project_id

    def track_claude(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        shot_index: int = -1,
        description: str = "",
    ):
        """Record a Claude API call."""
        pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["default"])
        # Cached tokens are half price
        effective_input = input_tokens - cached_tokens + cached_tokens * 0.5
        cost = (effective_input * pricing[0] + output_tokens * pricing[1]) / 1_000_000

        call = APICall(
            timestamp=datetime.now().isoformat(),
            service="claude",
            model=model,
            project_id=self._current_project,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            estimated_cost_usd=round(cost, 6),
            shot_index=shot_index,
            description=description,
        )

        with self._lock:
            self._calls.append(call)

        self._auto_save()
        return call

    def track_higgsfield(
        self,
        duration_sec: float,
        resolution: str = "720p",
        generation_id: str = "",
        shot_index: int = -1,
        description: str = "",
    ):
        """Record a Higgsfield API call."""
        rate = HIGGSFIELD_PRICING.get(resolution, HIGGSFIELD_PRICING["default"])
        cost = duration_sec * rate

        call = APICall(
            timestamp=datetime.now().isoformat(),
            service="higgsfield",
            model="higgsfield-video",
            project_id=self._current_project,
            duration_sec=duration_sec,
            resolution=resolution,
            generation_id=generation_id,
            estimated_cost_usd=round(cost, 4),
            shot_index=shot_index,
            description=description,
        )

        with self._lock:
            self._calls.append(call)

        self._auto_save()
        return call

    def get_project_summary(self, project_id: str | None = None) -> dict:
        """Get cost summary for a project."""
        pid = project_id or self._current_project
        calls = [c for c in self._calls if c.project_id == pid] if pid else self._calls

        claude_calls = [c for c in calls if c.service == "claude"]
        hf_calls = [c for c in calls if c.service == "higgsfield"]

        total_input = sum(c.input_tokens for c in claude_calls)
        total_output = sum(c.output_tokens for c in claude_calls)
        total_cached = sum(c.cached_tokens for c in claude_calls)
        claude_cost = sum(c.estimated_cost_usd for c in claude_calls)

        hf_duration = sum(c.duration_sec for c in hf_calls)
        hf_cost = sum(c.estimated_cost_usd for c in hf_calls)

        return {
            "project_id": pid or "(all)",
            "total_api_calls": len(calls),
            "claude": {
                "calls": len(claude_calls),
                "input_tokens": total_input,
                "output_tokens": total_output,
                "cached_tokens": total_cached,
                "total_tokens": total_input + total_output,
                "estimated_cost_usd": round(claude_cost, 4),
            },
            "higgsfield": {
                "calls": len(hf_calls),
                "total_duration_sec": round(hf_duration, 1),
                "estimated_cost_usd": round(hf_cost, 4),
            },
            "total_estimated_cost_usd": round(claude_cost + hf_cost, 4),
        }

    def get_project_detail(self, project_id: str | None = None) -> list[dict]:
        """Get detailed call log for a project."""
        pid = project_id or self._current_project
        calls = [c for c in self._calls if c.project_id == pid] if pid else self._calls
        return [self._call_to_dict(c) for c in calls]

    def export_csv(self, output_path: str | Path, project_id: str | None = None) -> Path:
        """Export call log as CSV."""
        output_path = Path(output_path)
        pid = project_id or self._current_project
        calls = [c for c in self._calls if c.project_id == pid] if pid else self._calls

        headers = [
            "timestamp", "service", "model", "project_id",
            "input_tokens", "output_tokens", "cached_tokens",
            "duration_sec", "resolution", "estimated_cost_usd",
            "shot_index", "description",
        ]

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for c in calls:
                row = [
                    c.timestamp, c.service, c.model, c.project_id,
                    str(c.input_tokens), str(c.output_tokens), str(c.cached_tokens),
                    str(c.duration_sec), c.resolution, str(c.estimated_cost_usd),
                    str(c.shot_index), f'"{c.description}"',
                ]
                f.write(",".join(row) + "\n")

        return output_path

    def _auto_save(self):
        if self._storage_dir:
            self._save()

    def _save(self):
        path = self._storage_dir / "cost_log.json"
        data = [self._call_to_dict(c) for c in self._calls]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self):
        path = self._storage_dir / "cost_log.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self._calls = [self._dict_to_call(d) for d in data]
            log.info("Loaded %d cost records", len(self._calls))

    @staticmethod
    def _call_to_dict(c: APICall) -> dict:
        return {
            "timestamp": c.timestamp, "service": c.service, "model": c.model,
            "project_id": c.project_id,
            "input_tokens": c.input_tokens, "output_tokens": c.output_tokens,
            "cached_tokens": c.cached_tokens,
            "duration_sec": c.duration_sec, "resolution": c.resolution,
            "generation_id": c.generation_id,
            "estimated_cost_usd": c.estimated_cost_usd,
            "shot_index": c.shot_index, "description": c.description,
        }

    @staticmethod
    def _dict_to_call(d: dict) -> APICall:
        return APICall(**{k: v for k, v in d.items() if k in APICall.__dataclass_fields__})


# ── Singleton ──

_tracker: CostTracker | None = None


def get_tracker() -> CostTracker:
    global _tracker
    if _tracker is None:
        from director.config import get_config
        cfg = get_config()
        _tracker = CostTracker(cfg.output_dir / "costs")
    return _tracker
