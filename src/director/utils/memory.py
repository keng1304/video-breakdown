"""Memory monitoring and model lifecycle management."""

from __future__ import annotations

import gc
import logging
from contextlib import contextmanager

import psutil

log = logging.getLogger(__name__)


def get_process_memory_gb() -> float:
    """Current process RSS in GB."""
    return psutil.Process().memory_info().rss / (1024 ** 3)


@contextmanager
def model_scope(name: str, budget_gb: float = 8.0):
    """Context manager for model lifecycle. Logs memory and cleans up on exit."""
    mem_before = get_process_memory_gb()
    log.info("[%s] Loading — memory: %.2f GB", name, mem_before)
    try:
        yield
    finally:
        # Force cleanup
        gc.collect()
        try:
            import torch
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except (ImportError, AttributeError):
            pass

        mem_after = get_process_memory_gb()
        delta = mem_after - mem_before
        log.info("[%s] Unloaded — memory: %.2f GB (delta: %+.2f GB)", name, mem_after, delta)
        if mem_after > budget_gb:
            log.warning("[%s] Memory %.2f GB exceeds budget %.2f GB", name, mem_after, budget_gb)
