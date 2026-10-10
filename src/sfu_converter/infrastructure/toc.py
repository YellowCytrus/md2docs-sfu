from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from sfu_converter.domain.constants import APPENDIX_LETTERS, APPENDIX_TITLE, EN_DASH
from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    Document,
    HeadingNode,
    StructuralSectionNode,
    StructuralSectionType,
    TableOfContentsNode,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile
from sfu_converter.infrastructure.numbering import build_numbering_context


_APPENDIX_LETTER_BY_VALUE = {letter: index for index, letter in enumerate(APPENDIX_LETTERS)}
_APPENDIX_TITLE_RE = re.compile(rf"\b{APPENDIX_TITLE}\s+([А-Я])\b", re.IGNORECASE)


@dataclass(frozen=True)
class TocEntry:
    text: str
    level: int
    page: int | tuple[int, int] | None
    left_indent_cm: float

    @property
    def rendered_text(self) -> str:
        if self.page is None:
            return self.text
        if isinstance(self.page, tuple):
            page_text = f"{self.page[0]}{EN_DASH}{self.page[1]}"
        else:
            page_text = str(self.page)
        return f"{self.text}\t{page_text}"


@dataclass(frozen=True)
class TocField:
    title: str
    levels: int
    entries: tuple[TocEntry, ...]
    diagnostics: tuple[Diagnostic, ...]
    should_insert: bool
    explicit: bool
    layout: str = "standard"


def build_toc_field(
    document: Document,
    *,
    profile: FormattingProfile,
    total_pages: int | None,
) -> TocField:
    explicit_node = _first_explicit_toc(document)
    explicit = explicit_node is not None
    title = explicit_node.title if isinstance(explicit_node, TableOfContentsNode) else "СОДЕРЖАНИЕ"
    levels = explicit_node.levels if isinstance(explicit_node, TableOfContentsNode) else 4
    total = int(total_pages or 0)
    is_short = 0 < total <= 24
    diagnostics: list[Diagnostic] = []

    if is_short and profile.name != "graduation_qualification_work":
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.TOC_NOT_REQUIRED_FOR_SHORT_DOCUMENT,
                message="Contents are not recommended for documents of 24 pages or less",
                severity=Severity.INFO,
                rule_id="common.toc.required_for_length",
                data={"total_pages": total},
            )
        )

    should_insert = explicit or total > 24 or profile.name == "graduation_qualification_work"
    if is_short and not explicit and profile.name != "graduation_qualification_work":
        should_insert = False

    return TocField(
        title=title,
        levels=levels,
        entries=_collect_entries(document, profile=profile, levels=levels, total_pages=total),
        diagnostics=tuple(diagnostics),
        should_insert=should_insert,
        explicit=explicit,
        layout=_layout_name(document, profile),
    )


def _first_explicit_toc(document: Document) -> TableOfContentsNode | StructuralSectionNode | None:
    for block in document.blocks:
        if isinstance(block, TableOfContentsNode):
            return block
        if isinstance(block, StructuralSectionNode) and block.section_type is StructuralSectionType.CONTENTS:
            return block
    return None


def _layout_name(document: Document, profile: FormattingProfile) -> str:
    if profile.name == "coursework" and _truthy(document.metadata.get("course_work")):
        return "form_t"
    return "standard"


def _truthy(value: object) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y", "да"}


def _collect_entries(
    document: Document,
    *,
    profile: FormattingProfile,
    levels: int,
    total_pages: int,
) -> tuple[TocEntry, ...]:
    entries: list[TocEntry] = []
    numbering = build_numbering_context(profile)
    blocks = tuple(document.blocks)
    page_numbers = _page_number_stream(total_pages)
    index = 0

    while index < len(blocks):
        block = blocks[index]
        if isinstance(block, HeadingNode):
            if block.level.value <= levels:
                entries.append(
                    TocEntry(
                        text=_heading_text(block, numbering),
                        level=block.level.value,
                        page=next(page_numbers),
                        left_indent_cm=_indent_for_level(block.level.value),
                    )
                )
        elif isinstance(block, StructuralSectionNode):
            if block.section_type is not StructuralSectionType.CONTENTS:
                entries.append(
                    TocEntry(
                        text=_contents_case(block.title),
                        level=1,
                        page=next(page_numbers),
                        left_indent_cm=0,
                    )
                )
        elif isinstance(block, AppendixNode):
            appendix_group = _take_appendix_group(blocks[index:])
            entries.extend(_appendix_entries(appendix_group, page_numbers))
            index += len(appendix_group) - 1
        index += 1

    return tuple(entries)


def _heading_text(block: HeadingNode, numbering) -> str:
    if block.number != "auto":
        return block.text.strip()
    number = numbering.next_section_number(block.level)
    title = block.text.rstrip().removesuffix(".")
    return f"{number} {title}"


def _contents_case(value: str) -> str:
    text = " ".join((value or "").strip().split())
    if not text:
        return text
    letters = [char for char in text if char.isalpha()]
    if letters and all(char.isupper() for char in letters):
        return text[:1] + text[1:].lower()
    return text


def _indent_for_level(level: int) -> float:
    return max(level - 1, 0) * 0.5


def _take_appendix_group(blocks: Iterable) -> tuple[AppendixNode, ...]:
    group: list[AppendixNode] = []
    for block in blocks:
        if not isinstance(block, AppendixNode):
            break
        group.append(block)
    return tuple(group)


def _appendix_entries(
    appendices: tuple[AppendixNode, ...],
    page_numbers,
) -> tuple[TocEntry, ...]:
    letters = tuple(_appendix_letter(block) for block in appendices)
    if len(appendices) >= 3 and _letters_are_contiguous(letters):
        pages = tuple(next(page_numbers) for _ in appendices)
        return (
            TocEntry(
                text=f"Приложения {letters[0]}{EN_DASH}{letters[-1]}",
                level=1,
                page=(pages[0], pages[-1]),
                left_indent_cm=0,
            ),
        )

    entries: list[TocEntry] = []
    for block in appendices:
        entries.append(
            TocEntry(
                text=_appendix_entry_text(block),
                level=1,
                page=next(page_numbers),
                left_indent_cm=0,
            )
        )
    return tuple(entries)


def _appendix_letter(block: AppendixNode) -> str:
    if block.letter:
        return block.letter.upper()
    match = _APPENDIX_TITLE_RE.search(block.title or "")
    return match.group(1).upper() if match else ""


def _appendix_entry_text(block: AppendixNode) -> str:
    letter = _appendix_letter(block)
    prefix = f"Приложение {letter}".strip()
    title = (block.subtitle or "").strip()
    return f"{prefix} {title}".strip()


def _letters_are_contiguous(letters: tuple[str, ...]) -> bool:
    if not letters or any(letter not in _APPENDIX_LETTER_BY_VALUE for letter in letters):
        return False
    positions = [_APPENDIX_LETTER_BY_VALUE[letter] for letter in letters]
    return positions == list(range(positions[0], positions[0] + len(positions)))


def _page_number_stream(total_pages: int):
    current = 1
    upper = max(total_pages, 1)
    while True:
        yield min(current, upper)
        current += 1
