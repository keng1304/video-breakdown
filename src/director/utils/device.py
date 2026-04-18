"""Device selection: CoreML > MPS > CPU."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def get_onnx_providers() -> list[str]:
    """Return ONNX Runtime execution providers in priority order."""
    try:
        import onnxruntime as ort
        available = ort.get_available_providers()
    except ImportError:
        return ["CPUExecutionProvider"]

    priority = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    selected = [p for p in priority if p in available]
    log.info("ONNX providers: %s", selected)
    return selected or ["CPUExecutionProvider"]


def get_torch_device() -> str:
    """Return best available PyTorch device string."""
    try:
        import torch
        if torch.backends.mps.is_available():
            log.info("PyTorch device: mps")
            return "mps"
    except (ImportError, AttributeError):
        pass
    log.info("PyTorch device: cpu")
    return "cpu"


def has_coreml() -> bool:
    """Check if CoreML execution provider is available."""
    try:
        import onnxruntime as ort
        return "CoreMLExecutionProvider" in ort.get_available_providers()
    except ImportError:
        return False
