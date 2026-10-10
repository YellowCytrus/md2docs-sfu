from __future__ import annotations

from abc import ABC, abstractmethod

from sfu_converter.domain.ast_nodes import Document
from sfu_converter.domain.diagnostics import Diagnostic
from sfu_converter.domain.formatting import FormattingProfile


class RendererPort(ABC):
    @abstractmethod
    def render(
        self,
        document: Document,
        profile: FormattingProfile,
        template_path: str | None = None,
        template_mode: str = "append",
        skip_generated_front_matter: bool = False,
    ) -> bytes:
        """Render a Document AST to DOCX bytes."""

    @abstractmethod
    def render_to_file(
        self,
        document: Document,
        profile: FormattingProfile,
        output_path: str,
        template_path: str | None = None,
        template_mode: str = "append",
        skip_generated_front_matter: bool = False,
    ) -> list[Diagnostic]:
        """Render a Document AST to a DOCX file."""
