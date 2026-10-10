from __future__ import annotations

from abc import ABC, abstractmethod


class FileReaderPort(ABC):
    @abstractmethod
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read text from a storage location."""


class FileWriterPort(ABC):
    @abstractmethod
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to a storage location."""
