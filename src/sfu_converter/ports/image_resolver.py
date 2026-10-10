from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ImageResolverPort(ABC):
    @abstractmethod
    def resolve_image(self, image_path: str) -> Path | None:
        """Resolve an image reference to a readable path."""
