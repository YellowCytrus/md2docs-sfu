from __future__ import annotations

import re
from collections.abc import Iterable

from sfu_converter.domain.ast_nodes import (
    AbbreviationEntryNode,
    AbbreviationsListNode,
    AppendixNode,
    Document,
    ParagraphNode,
    TableNode,
)

_SHORT_IN_PARENS_RE = re.compile(
    r"(?P<long>[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z0-9-]*(?:\s+[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z0-9-]*){1,5})"
    r"\s*\((?P<short>[А-ЯA-Z]{2,})\)"
)
_SHORT_BEFORE_LONG_RE = re.compile(r"\b(?P<short>[А-ЯA-Z]{2,})\b\s*\((?P<long>[^)]+)\)")
_WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z0-9-]*")

EXCLUDED_ABBREVIATIONS = frozenset(
    {
        "ГОСТ",
        "СТУ",
        "СП",
        "ВКР",
        "ДП",
        "КР",
        "КП",
    }
)
_LEADING_CONTEXT_WORDS = frozenset(
    {
        "в",
        "во",
        "на",
        "для",
        "работе",
        "тексте",
        "проекте",
        "методика",
        "отчете",
        "отчёте",
        "используется",
        "использует",
        "применяется",
        "рассматривается",
        "описан",
        "описана",
        "описано",
    }
)


def collect_abbreviations(document: Document) -> tuple[AbbreviationEntryNode, ...]:
    """Return unique abbreviation introductions sorted by abbreviation."""

    entries_by_short: dict[str, AbbreviationEntryNode] = {}
    for text in _iter_text(document.blocks):
        for short, long in _find_abbreviations(text):
            if short in entries_by_short:
                continue
            entries_by_short[short] = AbbreviationEntryNode(short=short, long=long)
    return tuple(sorted(entries_by_short.values(), key=lambda entry: entry.short.casefold()))


def explicit_abbreviations(document: Document) -> tuple[AbbreviationEntryNode, ...] | None:
    for block in document.blocks:
        if isinstance(block, AbbreviationsListNode):
            return block.entries
    return None


def abbreviations_for_document(document: Document) -> tuple[AbbreviationEntryNode, ...]:
    explicit = explicit_abbreviations(document)
    if explicit is not None:
        return explicit
    return collect_abbreviations(document)


def _find_abbreviations(text: str) -> Iterable[tuple[str, str]]:
    for match in _SHORT_IN_PARENS_RE.finditer(text):
        short = match.group("short").strip()
        if short in EXCLUDED_ABBREVIATIONS:
            continue
        long = _trim_long_phrase(match.group("long"))
        if long:
            yield short, long

    for match in _SHORT_BEFORE_LONG_RE.finditer(text):
        short = match.group("short").strip()
        if short in EXCLUDED_ABBREVIATIONS:
            continue
        long = _normalize_long(match.group("long"))
        if long and not long.isupper():
            yield short, long


def _iter_text(blocks: Iterable[object]) -> Iterable[str]:
    for block in blocks:
        if isinstance(block, ParagraphNode):
            yield "".join(getattr(run, "text", "") for run in block.runs)
        elif isinstance(block, TableNode):
            for row in block.rows:
                for cell in row.cells:
                    yield cell.text
        elif isinstance(block, AppendixNode):
            yield from _iter_text(block.blocks)


def _trim_long_phrase(value: str) -> str:
    words = _WORD_RE.findall(value)
    words = _drop_leading_context(words)
    if len(words) > 4:
        words = words[-4:]
        words = _drop_leading_context(words)
    return _normalize_long(" ".join(words))


def _drop_leading_context(words: list[str]) -> list[str]:
    words = list(words)
    while len(words) > 2 and words[0].casefold() in _LEADING_CONTEXT_WORDS:
        words.pop(0)
    return words


def _normalize_long(value: str) -> str:
    return " ".join(value.strip(" ,;:-").split())
