from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from sfu_converter.domain.ast_nodes import Citation, CitationNode, SourceSpan, TextRun
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity

TextRunParser = Callable[[str], Iterable]

_CITATION_CANDIDATE_RE = re.compile(r"\[(?P<inner>\d[^\]]*)\]")
_CITATION_SEGMENT_RE = re.compile(
    r"^\s*"
    r"(?P<number>\d+)"
    r"(?:\s*,\s*т\.\s*(?P<volume>\d+))?"
    r"(?:\s*,\s*с\.\s*(?P<page_start>\d+)(?:\s*[-–—]\s*(?P<page_end>\d+))?)?"
    r"\s*$",
    re.IGNORECASE,
)


def parse_citation_text(text: str, source: SourceSpan | None = None) -> CitationNode:
    node, diagnostics = try_parse_citation_text(text, source)
    if diagnostics or node is None:
        message = diagnostics[0].message if diagnostics else f"Malformed citation: {text}"
        raise ValueError(message)
    return node


def try_parse_citation_text(
    text: str,
    source: SourceSpan | None = None,
) -> tuple[CitationNode | None, list[Diagnostic]]:
    inner = text.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]

    citations: list[Citation] = []
    diagnostics: list[Diagnostic] = []
    seen_numbers: set[int] = set()

    for raw_segment in inner.split(";"):
        match = _CITATION_SEGMENT_RE.fullmatch(raw_segment)
        if match is None:
            return None, [_citation_diagnostic(DiagnosticCodes.CITATION_MALFORMED, text, source)]

        number = int(match.group("number"))
        if number in seen_numbers:
            diagnostics.append(_citation_diagnostic(DiagnosticCodes.CITATION_NUMBER_DUPLICATED, text, source))
        seen_numbers.add(number)

        page_start = match.group("page_start")
        page_end = match.group("page_end")
        pages = None
        if page_start is not None and page_end is not None:
            start = int(page_start)
            end = int(page_end)
            if start > end:
                diagnostics.append(_citation_diagnostic(DiagnosticCodes.CITATION_PAGE_RANGE_REVERSED, text, source))
            pages = (start, end)
        elif page_start is not None:
            pages = int(page_start)

        volume = match.group("volume")
        citations.append(
            Citation(
                number=number,
                volume=int(volume) if volume is not None else None,
                pages=pages,
            )
        )

    if diagnostics:
        return None, diagnostics
    return CitationNode(citations=tuple(citations), source=source), []


def split_citation_runs(
    text: str,
    *,
    source: SourceSpan | None = None,
    diagnostics: list[Diagnostic] | None = None,
    parse_text: TextRunParser | None = None,
) -> tuple:
    parse_text = parse_text or (lambda value: (TextRun(value, source=source),) if value else ())
    runs: list = []
    cursor = 0
    for match in _CITATION_CANDIDATE_RE.finditer(text):
        if match.start() > cursor:
            runs.extend(parse_text(text[cursor : match.start()]))

        token = match.group(0)
        node, token_diagnostics = try_parse_citation_text(token, source)
        if token_diagnostics:
            if diagnostics is not None:
                diagnostics.extend(token_diagnostics)
            runs.extend(parse_text(token))
        elif node is not None:
            runs.append(node)
        cursor = match.end()

    if cursor < len(text):
        runs.extend(parse_text(text[cursor:]))
    if not runs:
        runs.extend(parse_text(text))
    return _coalesce_text_runs(runs)


def starts_with_citation(text: str) -> bool:
    return _CITATION_CANDIDATE_RE.match(text.strip()) is not None


def format_citation_node(node: CitationNode) -> str:
    return node.text


def _citation_diagnostic(code: str, text: str, source: SourceSpan | None) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=f"Invalid source citation {text!r}",
        severity=Severity.ERROR,
        source=source,
        rule_id="common.reference.cross_check",
    )


def _coalesce_text_runs(runs: list) -> tuple:
    coalesced: list = []
    for run in runs:
        if (
            coalesced
            and isinstance(run, TextRun)
            and isinstance(coalesced[-1], TextRun)
            and run.bold == coalesced[-1].bold
            and run.italic == coalesced[-1].italic
            and run.source == coalesced[-1].source
        ):
            previous = coalesced[-1]
            coalesced[-1] = TextRun(
                text=previous.text + run.text,
                bold=previous.bold,
                italic=previous.italic,
                source=previous.source,
            )
        else:
            coalesced.append(run)
    return tuple(coalesced)
