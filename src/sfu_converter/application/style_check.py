from __future__ import annotations

import re
from collections.abc import Iterable

from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    CitationNode,
    Document,
    DrawingSheetNode,
    FigureNode,
    FootnoteAnchor,
    HeadingNode,
    InlineNode,
    ListNode,
    ParagraphNode,
    PosterNode,
    ProjectDesignationNode,
    RawBlockNode,
    SectionSetupNode,
    SlideDeckNode,
    SourceSpan,
    StructuralSectionNode,
    TableCaptionNode,
    TableNode,
    TextRun,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity

_ABBREVIATION_RE = re.compile(r"(?<![\w])([A-ZА-ЯЁ]{2,})(?![\w])")
_INTRODUCTION_RE = re.compile(
    r"(?P<long>[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9.,;:\- ]{2,}?)"
    r"\s*\((?P<short>[A-ZА-ЯЁ]{2,})\)"
)


def find_abbreviations(blocks: Iterable[object]) -> list[tuple[str, str, SourceSpan | None]]:
    introductions: list[tuple[str, str, SourceSpan | None]] = []
    for item in _iter_text_items(blocks):
        for match in _INTRODUCTION_RE.finditer(item.text):
            introductions.append(
                (
                    match.group("short"),
                    _clean_long_form(match.group("long")),
                    item.source,
                )
            )
    return introductions


def validate_style(document: Document) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    introduced: set[str] = set()
    reported_missing: set[str] = set()

    for item in _iter_text_items(document.blocks):
        introduction_spans = _introduction_spans(item.text)
        if item.forbids_abbreviations:
            diagnostics.extend(_heading_abbreviation_diagnostics(item))

        for match in _ABBREVIATION_RE.finditer(item.text):
            short = match.group(1)
            intro = _introduction_covering(match.start(), match.end(), introduction_spans)
            if intro is not None:
                introduced.add(short)
                continue
            if short in introduced or short in reported_missing:
                continue
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.STYLE_ABBREVIATION_NOT_INTRODUCED,
                    message=f"Abbreviation '{short}' is used before introduction",
                    severity=Severity.WARNING,
                    rule_id="common.style.abbreviation_introduction",
                    source=item.source,
                    data={"abbreviation": short},
                )
            )
            reported_missing.add(short)

        for short, _, _ in introduction_spans:
            introduced.add(short)

    return diagnostics


class _TextItem:
    def __init__(
        self,
        text: str,
        source: SourceSpan | None,
        *,
        forbids_abbreviations: bool = False,
    ):
        self.text = text
        self.source = source
        self.forbids_abbreviations = forbids_abbreviations


def _iter_text_items(blocks: Iterable[object]) -> Iterable[_TextItem]:
    for block in blocks:
        if isinstance(block, ParagraphNode):
            yield _TextItem(_inline_text(block.runs), block.source)
        elif isinstance(block, HeadingNode):
            yield _TextItem(block.text, block.source, forbids_abbreviations=True)
        elif isinstance(block, StructuralSectionNode):
            yield _TextItem(block.title, block.source, forbids_abbreviations=True)
        elif isinstance(block, AppendixNode):
            yield _TextItem(block.title, block.source, forbids_abbreviations=True)
            yield from _iter_text_items(block.blocks)
        elif isinstance(block, TableCaptionNode):
            yield _TextItem(block.text, block.source, forbids_abbreviations=True)
        elif isinstance(block, FigureNode):
            if block.caption:
                yield _TextItem(block.caption, block.source, forbids_abbreviations=True)
        elif isinstance(block, TableNode):
            if block.caption:
                yield _TextItem(block.caption, block.source, forbids_abbreviations=True)
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
        elif isinstance(block, RawBlockNode):
            yield _TextItem(block.text, block.source)
        elif isinstance(block, ProjectDesignationNode):
            continue
        elif isinstance(block, DrawingSheetNode):
            if block.designation:
                yield _TextItem(block.designation, block.source)
        elif isinstance(block, PosterNode):
            yield _TextItem(block.title, block.source, forbids_abbreviations=True)
            yield from _iter_text_items(block.blocks)
        elif isinstance(block, SlideDeckNode):
            for slide in block.slides:
                for value in slide.fields.values():
                    yield _TextItem(str(value), slide.source)
                for line in slide.body:
                    yield _TextItem(line, slide.source)
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


def _introduction_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    for match in _INTRODUCTION_RE.finditer(text):
        short = match.group("short")
        short_start = match.start("short")
        short_end = match.end("short")
        spans.append((short, short_start, short_end))
    return spans


def _introduction_covering(
    start: int,
    end: int,
    spans: list[tuple[str, int, int]],
) -> tuple[str, int, int] | None:
    for span in spans:
        _, span_start, span_end = span
        if span_start <= start and end <= span_end:
            return span
    return None


def _heading_abbreviation_diagnostics(item: _TextItem) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in _ABBREVIATION_RE.finditer(item.text):
        short = match.group(1)
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STYLE_ABBREVIATION_IN_HEADING,
                message=f"Abbreviation '{short}' is not allowed in headings or captions",
                severity=Severity.WARNING,
                rule_id="common.style.no_abbreviations_in_headings",
                source=item.source,
                data={"abbreviation": short},
            )
        )
    return diagnostics


def _clean_long_form(text: str) -> str:
    words = " ".join(text.split()).split()
    while words and words[0][-1:] in {".", ",", ";", ":"}:
        words = words[1:]
    return " ".join(words).strip(" .,;:")
