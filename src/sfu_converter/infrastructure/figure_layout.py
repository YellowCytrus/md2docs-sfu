from __future__ import annotations

import re
from collections.abc import Iterable

from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    Document,
    FigureNode,
    HeadingNode,
    ParagraphNode,
    RawBlockNode,
    ReferenceNode,
    StructuralSectionNode,
    TableCaptionNode,
)
from sfu_converter.domain.constants import DASH_SEPARATOR, EN_DASH
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.reference_graph import ReferenceGraph, ReferenceTargetKind, build_reference_graph

_FIRST_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)


def capitalize_caption(text: str) -> str:
    """Uppercase the first letter of a caption, leaving the rest untouched."""

    match = _FIRST_LETTER_RE.search(text)
    if match is None:
        return text
    index = match.start()
    return f"{text[:index]}{text[index].upper()}{text[index + 1:]}"


def normalize_figure_caption(text: str) -> str:
    """Normalise dashes and uppercase the descriptive part of a caption.

    ``Рисунок 1 - схема`` becomes ``Рисунок 1 — Схема``. A caption that already
    carries the ``Рисунок N`` prefix has only its descriptive tail capitalised.
    """

    text = normalize_caption_dashes(text)
    match = re.match(
        rf"^(Рисунок\s+\S+)\s*{re.escape(DASH_SEPARATOR)}\s*(.+)$",
        text,
    )
    if match:
        return f"{match.group(1)}{DASH_SEPARATOR}{capitalize_caption(match.group(2))}"
    return capitalize_caption(text)


def figure_caption_text(block: FigureNode, number: str) -> str | None:
    if block.sheet is not None and block.sheet >= 2:
        return f"Рисунок {number}, лист {block.sheet}"

    caption = (block.caption or "").strip()
    if not caption:
        return None
    if caption.startswith("Рисунок"):
        return normalize_figure_caption(caption)
    return f"Рисунок {number}{DASH_SEPARATOR}{capitalize_caption(caption)}"


def normalize_caption_dashes(text: str) -> str:
    return re.sub(rf"\s[-{EN_DASH}]\s", DASH_SEPARATOR, text)


def figure_reference_diagnostics(
    document: Document,
    graph: ReferenceGraph | None = None,
) -> list[Diagnostic]:
    graph = graph or build_reference_graph(document)
    diagnostics: list[Diagnostic] = []
    figure_blocks = _figure_blocks_by_canonical(document, graph)
    for definition in graph.definitions:
        if definition.kind is not ReferenceTargetKind.FIGURE:
            continue
        reference_position = graph.first_reference_position(ReferenceTargetKind.FIGURE, definition.canonical)
        block = figure_blocks.get(definition.canonical)
        if reference_position is None:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.FIGURE_NEVER_REFERENCED,
                    message=f"Figure '{definition.canonical}' is never referenced",
                    severity=Severity.WARNING,
                    rule_id="common.reference.figure_table_formula",
                    source=definition.source,
                    target=definition.canonical,
                )
            )
            continue

        if reference_position - definition.position > 3:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.FIGURE_PLACEMENT_NEXT_PAGE,
                    message=(
                        f"Figure '{definition.canonical}' appears more than three paragraphs "
                        "before its first reference"
                    ),
                    severity=Severity.INFO,
                    rule_id="common.figure.placement_after_reference",
                    source=block.source if block is not None else definition.source,
                    target=definition.canonical,
                )
            )
    return diagnostics


def _figure_blocks_by_canonical(document: Document, graph: ReferenceGraph) -> dict[str, FigureNode]:
    figures = [block for block in _walk_reference_blocks(document.blocks) if isinstance(block, FigureNode)]
    by_canonical: dict[str, FigureNode] = {}
    for definition in graph.definitions:
        if definition.kind is not ReferenceTargetKind.FIGURE:
            continue
        match = next((block for block in figures if block.source == definition.source), None)
        if match is not None:
            by_canonical[definition.canonical] = match
    return by_canonical


def _walk_reference_blocks(blocks: Iterable) -> Iterable:
    for block in blocks:
        if isinstance(
            block,
            (
                FigureNode,
                HeadingNode,
                ParagraphNode,
                RawBlockNode,
                ReferenceNode,
                StructuralSectionNode,
                TableCaptionNode,
            ),
        ):
            yield block
        elif isinstance(block, AppendixNode):
            yield from _walk_reference_blocks(block.blocks)
        else:
            yield block
