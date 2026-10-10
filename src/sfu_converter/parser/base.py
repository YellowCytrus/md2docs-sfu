from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sfu_converter.domain.ast_nodes import Document
from sfu_converter.domain.diagnostics import Diagnostic, Severity


@dataclass(frozen=True)
class ParserResult:
    document: Document
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.severity in (Severity.ERROR, Severity.FATAL) for diagnostic in self.diagnostics)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, source: str, filename: str | None = None) -> ParserResult:
        """Parse TXT source into a Document AST."""
