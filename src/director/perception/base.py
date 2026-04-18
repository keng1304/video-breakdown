"""Abstract base class for perception pipelines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PerceptionPipeline(ABC):
    """Base class enforcing load → process → unload lifecycle."""

    name: str = "base"

    @abstractmethod
    def load_model(self) -> None:
        """Load model weights into memory."""

    @abstractmethod
    def unload_model(self) -> None:
        """Release model from memory."""

    @abstractmethod
    def process(self, **kwargs) -> Any:
        """Run inference. Subclasses define their own kwargs and return types."""

    def estimate_memory_gb(self) -> float:
        """Estimated peak memory usage in GB."""
        return 1.0
