from __future__ import annotations

import re
from collections.abc import Iterable

from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    CitationNode,
    Document,
    FootnoteAnchor,
    HeadingNode,
    InlineNode,
    ListNode,
    ParagraphNode,
    SectionSetupNode,
    SourceSpan,
    StructuralSectionNode,
    TableCaptionNode,
    TableNode,
    TextRun,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity

QUANTITY_UNITS: dict[str, tuple[str, ...]] = {
    "mass": ("кг", "г"),
    "time": ("с", "мин", "ч"),
    "frequency": ("Гц",),
    "pressure": ("Па", "МПа"),
    "temperature": ("°C", "°С", "К"),
    "energy": ("Дж", "кВт·ч"),
    "length": ("м", "мм"),
}

_UNIT_TO_QUANTITY = {
    unit.casefold(): quantity
    for quantity, units in QUANTITY_UNITS.items()
    for unit in units
}
_UNIT_PATTERN = "|".join(re.escape(unit) for unit in sorted(_UNIT_TO_QUANTITY, key=len, reverse=True))
_MEASUREMENT_RE = re.compile(
    rf"(?P<value>\d+(?:[,.]\d+)?)\s*(?P<unit>{_UNIT_PATTERN})\b",
    flags=re.IGNORECASE,
)


def validate_unit_consistency(document: Document) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    section_units: dict[str, dict[str, list[SourceSpan | None]]] = {}

    for item in _iter_text_items(document.blocks):
        if item.starts_section:
            diagnostics.extend(_unit_diagnostics(section_units))
            section_units = {}

        paragraph_units: dict[str, dict[str, list[SourceSpan | None]]] = {}
        for unit in _units_in_text(item.text):
            quantity = item.quantity or _UNIT_TO_QUANTITY.get(unit.casefold())
            if quantity is None:
                continue
            paragraph_units.setdefault(quantity, {}).setdefault(unit, []).append(item.source)
            section_units.setdefault(quantity, {}).setdefault(unit, []).append(item.source)

        diagnostics.extend(_unit_diagnostics(paragraph_units))

    diagnostics.extend(_unit_diagnostics(section_units))
    return _deduplicate(diagnostics)


class _TextItem:
    def __init__(
        self,
        text: str,
        source: SourceSpan | None,
        *,
        quantity: str | None = None,
        starts_section: bool = False,
    ):
        self.text = text
        self.source = source
        self.quantity = quantity
        self.starts_section = starts_section


def _iter_text_items(blocks: Iterable[object]) -> Iterable[_TextItem]:
    for block in blocks:
        if isinstance(block, ParagraphNode):
            yield _TextItem(
                _inline_text(block.runs),
                block.source,
                quantity=block.metadata.get("quantity"),
            )
        elif isinstance(block, HeadingNode):
            yield _TextItem(block.text, block.source, starts_section=True)
        elif isinstance(block, StructuralSectionNode):
            yield _TextItem(block.title, block.source, starts_section=True)
        elif isinstance(block, AppendixNode):
            yield _TextItem(block.title, block.source, starts_section=True)
            yield from _iter_text_items(block.blocks)
        elif isinstance(block, TableCaptionNode):
            yield _TextItem(block.text, block.source)
        elif isinstance(block, TableNode):
            if block.caption:
                yield _TextItem(block.caption, block.source)
            for row in block.rows:
                for cell in row.cells:
                    yield _TextItem(cell.text, block.source)
        elif isinstance(block, ListNode):
            for item in block.items:
                if isinstance(item, ListNode):
                    yield from _iter_text_items((item,))
                else:
                    yield _TextItem(item.text, item.source)
                    yield from _iter_text_items(item.children)
        elif isinstance(block, SectionSetupNode):
            yield from _iter_text_items(block.blocks)
        elif hasattr(block, "blocks"):
            yield from _iter_text_items(getattr(block, "blocks"))


def _inline_text(runs: Iterable[InlineNode]) -> str:
    parts: list[str] = []
    for run in runs:
        if isinstance(run, TextRun):
            parts.append(run.text)
        elif isinstance(run, CitationNode):
            parts.append(run.text)
        elif isinstance(run, FootnoteAnchor):
            parts.append(run.marker)
    return "".join(parts)


def _units_in_text(text: str) -> list[str]:
    return [match.group("unit") for match in _MEASUREMENT_RE.finditer(text)]


def _unit_diagnostics(
    seen: dict[str, dict[str, list[SourceSpan | None]]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for quantity, units in seen.items():
        if len(units) <= 1:
            continue
        ordered_units = tuple(units.keys())
        spans = tuple(span for unit in ordered_units for span in units[unit])
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STYLE_UNIT_INCONSISTENT,
                message=(
                    f"Quantity '{quantity}' uses inconsistent units: "
                    f"{', '.join(ordered_units)}"
                ),
                severity=Severity.WARNING,
                rule_id="common.style.unit_consistency",
                data={
                    "quantity": quantity,
                    "units": ordered_units,
                    "spans": spans,
                },
            )
        )
    return diagnostics


def _deduplicate(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    result: list[Diagnostic] = []
    for diagnostic in diagnostics:
        key = (
            str(diagnostic.data.get("quantity") if diagnostic.data else ""),
            tuple(diagnostic.data.get("units", ()) if diagnostic.data else ()),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(diagnostic)
    return result
