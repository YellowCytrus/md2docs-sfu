"""Inline emphasis markup (``**bold**``, ``*italic*``) shared by parser and renderer.

Paragraph text is parsed into :class:`~sfu_converter.domain.ast_nodes.TextRun`
objects early, but table cells keep raw text in the AST (they are plain strings
used by many consumers). Both layers therefore need the same emphasis rules:
the parser splits paragraph text, and the DOCX renderer splits table-cell text
right before writing runs so that ``**bold**`` from Markdown tables survives.
"""

from __future__ import annotations

import re

from sfu_converter.domain.ast_nodes import SourceSpan, TextRun

_INLINE_FORMATTING_RE = re.compile(
    r"\*\*\*(\S(?:.*?\S)?)\*\*\*"
    r"|\*\*(\S(?:.*?\S)?)\*\*"
    r"|\*(\S(?:[^*]*?\S)?)\*"
)


def split_inline_markup(text: str, source: SourceSpan | None = None) -> tuple[TextRun, ...]:
    """Split ``text`` into runs by ``***bi***``, ``**bold**`` and ``*italic*``."""

    runs: list[TextRun] = []
    cursor = 0
    for match in _INLINE_FORMATTING_RE.finditer(text):
        start, end = match.span()
        if start > cursor:
            runs.append(TextRun(text=text[cursor:start], source=source))
        triple, bold, italic = match.group(1), match.group(2), match.group(3)
        if triple is not None:
            runs.append(TextRun(text=triple, bold=True, italic=True, source=source))
        elif bold is not None:
            runs.append(TextRun(text=bold, bold=True, source=source))
        else:
            runs.append(TextRun(text=italic, italic=True, source=source))
        cursor = end
    if cursor < len(text):
        runs.append(TextRun(text=text[cursor:], source=source))
    if not runs:
        return (TextRun(text=text, source=source),)
    return tuple(runs)


def strip_inline_markup(text: str) -> str:
    """Return ``text`` with emphasis markers removed and their content kept."""

    return _INLINE_FORMATTING_RE.sub(
        lambda match: match.group(1) or match.group(2) or match.group(3) or "",
        text,
    )
