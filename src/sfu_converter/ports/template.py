from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sfu_converter.domain.diagnostics import Diagnostic


class TemplateResolverPort(ABC):
    @abstractmethod
    def resolve_template(self, template_path: str | None) -> Path | None:
        """Resolve a template reference to a readable path."""


@dataclass(frozen=True)
class TemplateDocument:
    """A loaded DOCX template ready for inspection or composition."""

    doc: Any
    path: str


@dataclass(frozen=True)
class InsertionPoint:
    """Where generated content should be spliced into a template."""

    found: bool
    element: Any = None
    truncate: bool = True
    diagnostic: Diagnostic | None = None


class TemplatePort(ABC):
    """Adapter for composing generated content into a DOCX template."""

    @abstractmethod
    def load_template(self, path: str) -> TemplateDocument:
        """Load a DOCX template from disk."""

    @abstractmethod
    def find_insertion_point(
        self,
        template: TemplateDocument,
        mode: str,
        page: int | None = None,
        bookmark: str | None = None,
    ) -> InsertionPoint:
        """Locate the position inside the template where generated content begins."""

    @abstractmethod
    def compose(
        self,
        template: TemplateDocument,
        insertion_point: InsertionPoint,
        generated_content: bytes,
    ) -> bytes:
        """Splice generated content into the template at the insertion point."""
