from __future__ import annotations

import re
from dataclasses import replace

from sfu_converter.config import SyntaxConfig
from sfu_converter.domain.ast_nodes import (
    AbbreviationEntryNode,
    AbbreviationsListNode,
    AppendixNode,
    BibliographyEntryNode,
    Document,
    FigureNode,
    FormulaNode,
    FormulaSymbol,
    HeadingLevel,
    HeadingNode,
    ListItemNode,
    ListNode,
    ListType,
    MetadataNode,
    ParagraphNode,
    SourceSpan,
    StructuralSectionNode,
    StructuralSectionType,
    TableCaptionNode,
    TableCell,
    TableNote,
    TableNode,
    TableOfContentsNode,
    TableRow,
    TextRun,
    TitlePageNode,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.parser.attributes import parse_attributes
from sfu_converter.parser.base import BaseParser, ParserResult
from sfu_converter.parser.citations import split_citation_runs, starts_with_citation

_IMAGE_RE = re.compile(r"\[IMAGE(?:=([^\]]+))?\]")
_INLINE_FORMATTING_RE = re.compile(
    r"\*\*\*(\S(?:.*?\S)?)\*\*\*"
    r"|\*\*(\S(?:.*?\S)?)\*\*"
    r"|\*(\S(?:[^*]*?\S)?)\*"
)
_BIBLIOGRAPHY_ENTRY_RE = re.compile(r"^(\d+)\s+(.+)$")
_CYRILLIC_LATIN_MAP = {
    "А": "A",
    "В": "B",
    "С": "C",
    "Е": "E",
    "Н": "H",
    "К": "K",
    "М": "M",
    "О": "O",
    "Р": "P",
    "Т": "T",
    "Х": "X",
}
_CYRILLIC_RE = re.compile("[" + "".join(_CYRILLIC_LATIN_MAP.keys()) + "]")
_KNOWN_MARKERS = (
    "[H1]",
    "[H2]",
    "[H3]",
    "[H4]",
    "[IMAGE",
    "[LIST",
    "[LIST_END]",
    "[SECTION",
    "[STRUCTURAL",
    "[TABLE_START]",
    "[TABLE_END]",
    "[TABLE_CAPTION]",
    "[FORMULA",
    "[FORMULA_END]",
    "[FORMULA_EXPLANATION",
    "[FORMULA_EXPLANATION_END]",
    "[FORMULA_SYMBOL",
    "[TOC",
    "[META",
    "[TITLE_PAGE",
    "[ABBREVIATIONS_START]",
    "[ABBREVIATIONS_END]",
    "[ABBR",
)
_STRUCTURAL_SECTIONS_BY_TITLE = {
    **{section_type.value: section_type for section_type in StructuralSectionType},
    "СПИСОК ИСТОЧНИКОВ": StructuralSectionType.SOURCES,
}
_STRUCTURAL_TYPE_ALIASES = {
    "abstract": StructuralSectionType.ABSTRACT,
    "referat": StructuralSectionType.ABSTRACT,
    "annotation": StructuralSectionType.ANNOTATION,
    "contents": StructuralSectionType.CONTENTS,
    "content": StructuralSectionType.CONTENTS,
    "introduction": StructuralSectionType.INTRODUCTION,
    "intro": StructuralSectionType.INTRODUCTION,
    "conclusion": StructuralSectionType.CONCLUSION,
    "abbreviations": StructuralSectionType.ABBREVIATIONS,
    "sources": StructuralSectionType.SOURCES,
    "bibliography": StructuralSectionType.SOURCES,
    "appendix": StructuralSectionType.APPENDIX,
}
_LIST_TYPE_ALIASES = {
    "bullet": ListType.BULLET,
    "letter": ListType.LETTERED,
    "lettered": ListType.LETTERED,
    "number": ListType.NUMBERED,
    "numbered": ListType.NUMBERED,
}
_EXPLICIT_LIST_ITEM_RE = re.compile(r"^\[(?:-|[^\]]+\))\]\s*(.*)$")
_HEADING_MARKER_RE = re.compile(r"^\[H(\d+)\]")
_INDENTED_NUMERIC_ITEM_RE = re.compile(r"^(\s+)(\d+)\)\s+(.+)$")


def _heading_marker_level(stripped: str) -> int | None:
    match = _HEADING_MARKER_RE.match(stripped)
    return int(match.group(1)) if match is not None else None

APPENDIX_LETTERS: tuple[str, ...] = (
    "А",
    "Б",
    "В",
    "Г",
    "Д",
    "Е",
    "Ж",
    "И",
    "К",
    "Л",
    "М",
    "Н",
    "П",
    "Р",
    "С",
    "Т",
    "У",
    "Ф",
    "Х",
    "Ц",
    "Ш",
    "Щ",
)
_APPENDIX_LETTER_SET = frozenset(APPENDIX_LETTERS)
_APPENDIX_TYPES = frozenset({"обязательное", "справочное", "рекомендуемое"})
_APPENDIX_HEADER_RE = re.compile(
    r"^\[H1\]\s*ПРИЛОЖЕНИЕ(?:\s+(\S+))?\s*$",
    re.IGNORECASE,
)


class V1Parser(BaseParser):
    """Parser for v1 TXT syntax."""

    def parse(self, source: str, filename: str | None = None) -> ParserResult:
        lines = source.splitlines()
        blocks = []
        diagnostics: list[Diagnostic] = []
        in_bibliography = False
        last_heading_level = 0
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()
            span = _span_for_line(lines[i], i, filename)

            if not stripped:
                i += 1
                continue

            if stripped.startswith("["):
                self._check_cyrillic(stripped, span, diagnostics)

            if (heading_level := _heading_marker_level(stripped)) is not None:
                if heading_level >= 5:
                    diagnostics.append(
                        Diagnostic(
                            code=DiagnosticCodes.INVALID_HEADING_LEVEL,
                            message=f"Heading level {heading_level} is not allowed (max H4): {stripped}",
                            severity=Severity.ERROR,
                            source=span,
                        )
                    )
                elif heading_level == 1:
                    title = _HEADING_MARKER_RE.sub("", stripped, count=1).strip()
                    appendix_node, consumed = self._try_parse_appendix(lines, i, filename)
                    if appendix_node is not None:
                        blocks.append(appendix_node)
                        in_bibliography = False
                        last_heading_level = 1
                        i += consumed
                        continue
                    structural = _structural_section_from_title(title, span)
                    if structural is not None:
                        blocks.append(structural)
                        in_bibliography = structural.section_type is StructuralSectionType.SOURCES
                        last_heading_level = 1
                    else:
                        blocks.append(
                            HeadingNode(
                                level=HeadingLevel.H1,
                                text=title,
                                number="auto",
                                source=span,
                            )
                        )
                        in_bibliography = False
                        last_heading_level = 1
                else:
                    if heading_level > last_heading_level + 1:
                        diagnostics.append(
                            Diagnostic(
                                code=DiagnosticCodes.HEADING_LEVEL_SKIPPED,
                                message=(
                                    f"Heading jumped from level {last_heading_level} "
                                    f"to {heading_level}, skipping an intermediate level"
                                ),
                                severity=Severity.WARNING,
                                source=span,
                            )
                        )
                    blocks.append(
                        HeadingNode(
                            level=HeadingLevel(heading_level),
                            text=_HEADING_MARKER_RE.sub("", stripped, count=1).strip(),
                            number="auto",
                            source=span,
                        )
                    )
                    last_heading_level = heading_level
            elif _is_list_start(stripped):
                list_node, list_diagnostics, end_index = self._parse_explicit_list(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(list_diagnostics)
                if list_node is not None:
                    blocks.append(list_node)
                i = end_index
            elif stripped.startswith("[IMAGE"):
                figure = self._parse_image(stripped, span, diagnostics)
                if figure is not None:
                    caption, consumed = _caption_after_image(lines, i)
                    if caption is not None:
                        figure = FigureNode(src=figure.src, caption=caption, source=span)
                        i += consumed
                    blocks.append(figure)
            elif stripped.startswith("[SECTION"):
                structural = _parse_section_marker(stripped, span, diagnostics)
                if structural is not None:
                    blocks.append(structural)
                    in_bibliography = structural.section_type is StructuralSectionType.SOURCES
            elif stripped.startswith("[STRUCTURAL"):
                structural = _parse_structural_marker(stripped, span, diagnostics)
                if structural is not None:
                    blocks.append(structural)
                    in_bibliography = structural.section_type is StructuralSectionType.SOURCES
            elif stripped.startswith("[TABLE_START]"):
                table, table_diagnostics, end_index = self._parse_table(lines, i, filename)
                diagnostics.extend(table_diagnostics)
                if table is not None:
                    blocks.append(table)
                i = end_index
            elif stripped.startswith("[ABBREVIATIONS_START]"):
                abbreviations, abbreviation_diagnostics, end_index = self._parse_abbreviations(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(abbreviation_diagnostics)
                blocks.append(abbreviations)
                i = end_index
            elif stripped.startswith("[TABLE_CAPTION]"):
                blocks.append(
                    TableCaptionNode(
                        text=stripped.replace("[TABLE_CAPTION]", "", 1).strip(),
                        source=span,
                    )
                )
            elif stripped.startswith("[TOC"):
                toc_node = _parse_toc_marker(stripped, span)
                blocks.append(toc_node)
            elif stripped.startswith("[TITLE_PAGE"):
                blocks.append(_parse_title_page_marker(stripped, span))
            elif stripped.startswith("[META"):
                metadata_node = _parse_metadata_marker(stripped, span, diagnostics)
                if metadata_node is not None:
                    blocks.append(metadata_node)
            elif (
                stripped.startswith("[FORMULA_END]")
                or stripped.startswith("[FORMULA_EXPLANATION_END]")
                or stripped.startswith("[FORMULA_EXPLANATION]")
            ):
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
                        message=f"Unexpected marker outside formula block: {stripped}",
                        severity=Severity.ERROR,
                        source=span,
                    )
                )
            elif stripped.startswith("[FORMULA"):
                formula_node, formula_diagnostics, end_index = self._parse_formula(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(formula_diagnostics)
                blocks.append(formula_node)
                i = end_index
            elif stripped.startswith("[") and starts_with_citation(stripped):
                blocks.append(
                    ParagraphNode(
                        runs=_parse_inline_formatting(stripped, span, diagnostics),
                        source=span,
                    )
                )
            elif stripped.startswith("[") and not stripped.startswith(_KNOWN_MARKERS):
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
                        message=f"Unknown marker: {stripped}",
                        severity=Severity.WARNING,
                        source=span,
                    )
                )
            elif not stripped.startswith("["):
                if stripped.startswith("- "):
                    list_node, end_index = _parse_dash_list(lines, i, filename)
                    blocks.append(list_node)
                    i = end_index
                elif in_bibliography:
                    bibliography_match = _BIBLIOGRAPHY_ENTRY_RE.match(stripped)
                    if bibliography_match is not None:
                        blocks.append(
                            BibliographyEntryNode(
                                number=int(bibliography_match.group(1)),
                                text=bibliography_match.group(2).strip(),
                                source=span,
                            )
                        )
                    else:
                        blocks.append(
                            ParagraphNode(
                                runs=_parse_inline_formatting(stripped, span, diagnostics),
                                source=span,
                            )
                        )
                else:
                    blocks.append(
                        ParagraphNode(
                            runs=_parse_inline_formatting(stripped, span, diagnostics),
                            source=span,
                        )
                    )

            i += 1

        return ParserResult(
            document=Document(
                blocks=tuple(blocks),
                syntax_version=1,
                metadata=_collect_metadata(blocks),
                source_file=filename,
            ),
            diagnostics=diagnostics,
        )

    def _parse_image(
        self,
        stripped: str,
        span: SourceSpan,
        diagnostics: list[Diagnostic],
    ) -> FigureNode | None:
        match = _IMAGE_RE.fullmatch(stripped)
        if match is None:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message=f"Malformed IMAGE tag: {stripped}",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None

        image_path = match.group(1).strip() if match.group(1) else None
        return FigureNode(src=image_path, source=span)

    def _parse_formula(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[FormulaNode | None, list[Diagnostic], int]:
        """Parse ``[FORMULA]...[FORMULA_END]`` and optional explanation block."""

        diagnostics: list[Diagnostic] = []
        formula_start_span = _span_for_line(lines[start_index], start_index, filename)
        attrs = _parse_attributes(lines[start_index].strip())

        formula_lines: list[str] = []
        explanations: list[FormulaSymbol] = []
        i = start_index + 1
        found_end = False
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith("[FORMULA_END]"):
                found_end = True
                break
            if stripped.startswith("[FORMULA_SYMBOL"):
                explanations.append(_parse_formula_symbol(stripped))
                i += 1
                continue
            formula_lines.append(lines[i])
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="FORMULA without matching FORMULA_END",
                    severity=Severity.ERROR,
                    source=formula_start_span,
                )
            )
            line_end = len(lines)
            return (
                FormulaNode(
                    content=_formula_content(formula_lines),
                    id=attrs.get("id"),
                    number=attrs.get("number"),
                    explanations=tuple(explanations),
                    continuation_lines=_formula_continuation_lines(formula_lines),
                    source=SourceSpan(
                        line_start=formula_start_span.line_start,
                        line_end=line_end,
                        filename=filename,
                    ),
                ),
                diagnostics,
                i,
            )

        explanation: str | None = None
        explanation_end_index = i
        next_index = i + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index < len(lines) and lines[next_index].strip().startswith("[FORMULA_EXPLANATION]"):
            explanation_lines: list[str] = []
            j = next_index + 1
            explanation_found_end = False
            while j < len(lines):
                stripped_expl = lines[j].strip()
                if stripped_expl.startswith("[FORMULA_EXPLANATION_END]"):
                    explanation_found_end = True
                    break
                explanation_lines.append(lines[j])
                j += 1
            if not explanation_found_end:
                expl_start_span = _span_for_line(lines[next_index], next_index, filename)
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                        message=("FORMULA_EXPLANATION without matching FORMULA_EXPLANATION_END"),
                        severity=Severity.ERROR,
                        source=expl_start_span,
                    )
                )
            explanation = "\n".join(explanation_lines).strip("\n")
            explanation_end_index = j

        line_end = explanation_end_index + 1
        return (
            FormulaNode(
                content=_formula_content(formula_lines),
                id=attrs.get("id"),
                number=attrs.get("number"),
                explanation=explanation,
                explanations=tuple(explanations),
                continuation_lines=_formula_continuation_lines(formula_lines),
                source=SourceSpan(
                    line_start=formula_start_span.line_start,
                    line_end=line_end,
                    filename=filename,
                ),
            ),
            diagnostics,
            explanation_end_index,
        )

    def _parse_table(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[TableNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        rows: list[TableRow] = []
        notes: list[TableNote] = []
        expected_cell_count: int | None = None
        caption = None
        table_start_span = _span_for_line(lines[start_index], start_index, filename)
        i = start_index + 1
        found_end = False

        while i < len(lines):
            stripped = lines[i].strip()
            span = _span_for_line(lines[i], i, filename)

            if stripped.startswith("["):
                self._check_cyrillic(stripped, span, diagnostics)

            if stripped.startswith("[TABLE_END]"):
                found_end = True
                break
            if stripped.startswith("[TABLE_CAPTION]"):
                caption = stripped.replace("[TABLE_CAPTION]", "", 1).strip()
            elif stripped.startswith("[TABLE_NOTE"):
                attrs = _parse_attributes(stripped)
                notes.append(
                    TableNote(
                        marker=attrs.get("marker", "*"),
                        text=attrs.get("text", ""),
                        source=span,
                    )
                )
            elif stripped.startswith("|"):
                row = _parse_table_row(stripped)
                if row is None or _is_table_separator_row(row):
                    i += 1
                    continue
                cell_count = len(row.cells)
                if expected_cell_count is None:
                    expected_cell_count = cell_count
                elif cell_count != expected_cell_count:
                    diagnostics.append(
                        Diagnostic(
                            code=DiagnosticCodes.TXT_INVALID_TABLE_SHAPE,
                            message=(f"Table row has {cell_count} cells, expected {expected_cell_count}"),
                            severity=Severity.ERROR,
                            source=span,
                        )
                    )
                rows.append(row)
            elif stripped.startswith("[") and not stripped.startswith(_KNOWN_MARKERS):
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
                        message=f"Unknown marker inside table: {stripped}",
                        severity=Severity.WARNING,
                        source=span,
                    )
                )
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="TABLE_START without matching TABLE_END",
                    severity=Severity.ERROR,
                    source=table_start_span,
                )
            )

        line_end = i + 1 if found_end else len(lines)
        table = None
        if rows:
            table = TableNode(
                rows=tuple(rows),
                caption=caption,
                notes=tuple(notes),
                source=SourceSpan(
                    line_start=table_start_span.line_start,
                    line_end=line_end,
                    filename=filename,
                ),
            )
        return table, diagnostics, i

    def _parse_abbreviations(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[AbbreviationsListNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        entries: list[AbbreviationEntryNode] = []
        start_span = _span_for_line(lines[start_index], start_index, filename)
        i = start_index + 1
        found_end = False

        while i < len(lines):
            stripped = lines[i].strip()
            span = _span_for_line(lines[i], i, filename)
            if stripped.startswith("[ABBREVIATIONS_END]"):
                found_end = True
                break
            if stripped.startswith("[ABBR"):
                attrs = _parse_attributes(stripped)
                short = attrs.get("short", "").strip()
                long = attrs.get("long", "").strip()
                if short and long:
                    entries.append(AbbreviationEntryNode(short=short, long=long, source=span))
            elif stripped.startswith("|"):
                row = _parse_table_row(stripped)
                if row is not None and len(row.cells) >= 2 and not _is_table_separator_row(row):
                    entries.append(
                        AbbreviationEntryNode(
                            short=row.cells[0].text,
                            long=row.cells[1].text,
                            source=span,
                        )
                    )
            elif stripped:
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
                        message=f"Unknown marker inside abbreviations list: {stripped}",
                        severity=Severity.WARNING,
                        source=span,
                    )
                )
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="ABBREVIATIONS_START without matching ABBREVIATIONS_END",
                    severity=Severity.ERROR,
                    source=start_span,
                )
            )

        return (
            AbbreviationsListNode(
                entries=tuple(entries),
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=i + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _parse_explicit_list(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[ListNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        list_start_span = _span_for_line(lines[start_index], start_index, filename)
        attrs = _parse_attributes(lines[start_index].strip())
        list_type_name = attrs.get("type", "bullet").strip().lower()
        list_type = _LIST_TYPE_ALIASES.get(list_type_name)

        if list_type is None:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message=f"Unknown list type: {list_type_name or '<empty>'}",
                    severity=Severity.ERROR,
                    source=list_start_span,
                )
            )
            return None, diagnostics, start_index

        items: list[ListItemNode] = []
        i = start_index + 1
        found_end = False

        while i < len(lines):
            stripped = lines[i].strip()
            span = _span_for_line(lines[i], i, filename)

            if stripped.startswith("["):
                self._check_cyrillic(stripped, span, diagnostics)

            if stripped.startswith("[LIST_END]"):
                found_end = True
                break

            match = _EXPLICIT_LIST_ITEM_RE.fullmatch(stripped)
            if match is not None:
                items.append(ListItemNode(text=match.group(1).strip(), source=span))
            elif stripped:
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                        message=f"Malformed list item: {stripped}",
                        severity=Severity.ERROR,
                        source=span,
                    )
                )
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="LIST without matching LIST_END",
                    severity=Severity.ERROR,
                    source=list_start_span,
                )
            )

        line_end = i + 1 if found_end else len(lines)
        return (
            ListNode(
                list_type=list_type,
                items=tuple(items),
                source=SourceSpan(
                    line_start=list_start_span.line_start,
                    line_end=line_end,
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _check_cyrillic(
        self,
        text: str,
        span: SourceSpan,
        diagnostics: list[Diagnostic],
    ) -> None:
        bracket_end = text.find("]")
        if bracket_end == -1:
            marker_text = text[1:]
        else:
            marker_text = text[1:bracket_end]
        marker_text = re.split(r"[\s=]", marker_text, maxsplit=1)[0]

        if _CYRILLIC_RE.search(marker_text):
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_CYRILLIC_IN_MARKER,
                    message=f"Cyrillic characters detected in marker: [{marker_text}]",
                    severity=Severity.ERROR,
                    source=span,
                    suggestion="Replace Cyrillic lookalike characters with Latin equivalents",
                )
            )

    def _try_parse_appendix(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[AppendixNode | None, int]:
        """Detect ``[H1] ПРИЛОЖЕНИЕ X`` plus optional type and subtitle lines.

        Returns the parsed node and the number of consumed lines (>= 1) so the
        outer loop can advance past the heading and any companion lines.
        """

        first_line = lines[start_index].strip()
        match = _APPENDIX_HEADER_RE.match(first_line)
        if match is None:
            return None, 0

        letter = match.group(1).upper() if match.group(1) else None
        if letter is not None and letter not in _APPENDIX_LETTER_SET:
            return None, 0

        consumed = 1
        appendix_type: str | None = None
        subtitle: str | None = None
        cursor = start_index + 1

        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1

        if cursor < len(lines):
            candidate = lines[cursor].strip()
            if candidate.lower() in _APPENDIX_TYPES and not candidate.startswith("["):
                appendix_type = candidate.lower()
                consumed = cursor - start_index + 1
                cursor += 1
                while cursor < len(lines) and not lines[cursor].strip():
                    cursor += 1

        if cursor < len(lines):
            candidate = lines[cursor].strip()
            if (
                candidate
                and not candidate.startswith("[")
                and not _BIBLIOGRAPHY_ENTRY_RE.match(candidate)
                and appendix_type is not None
            ):
                subtitle = candidate
                consumed = cursor - start_index + 1

        title_parts = ["ПРИЛОЖЕНИЕ"]
        if letter:
            title_parts.append(letter)
        title = " ".join(title_parts)
        appendix_id = f"app:{letter.lower()}" if letter else None

        span = SourceSpan(
            line_start=start_index + 1,
            line_end=start_index + consumed,
            col_start=1,
            col_end=len(lines[start_index]),
            filename=filename,
        )
        return (
            AppendixNode(
                title=title,
                id=appendix_id,
                letter=letter,
                appendix_type=appendix_type,
                subtitle=subtitle,
                source=span,
            ),
            consumed,
        )


def _span_for_line(line: str, index: int, filename: str | None) -> SourceSpan:
    return SourceSpan(
        line_start=index + 1,
        line_end=index + 1,
        col_start=1 if line else 0,
        col_end=len(line),
        filename=filename,
    )


def _parse_table_row(stripped: str) -> TableRow | None:
    if not stripped.startswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return TableRow(cells=tuple(TableCell(text=cell) for cell in cells))


def _is_table_separator_row(row: TableRow) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.text.strip()) for cell in row.cells)


def _parse_dash_list(
    lines: list[str],
    start_index: int,
    filename: str | None,
) -> tuple[ListNode, int]:
    items: list[ListItemNode] = []
    i = start_index
    line_end = start_index

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("- "):
            items.append(
                ListItemNode(
                    text=stripped[2:].strip(),
                    source=_span_for_line(lines[i], i, filename),
                )
            )
            line_end = i
            i += 1
            continue

        nested_match = _INDENTED_NUMERIC_ITEM_RE.match(lines[i])
        if nested_match is not None and items:
            nested, nested_end = _parse_indented_numeric_list(lines, i, filename)
            last_item = items[-1]
            items[-1] = replace(last_item, children=(*last_item.children, nested))
            line_end = nested_end
            i = nested_end + 1
            continue

        break

    return (
        ListNode(
            list_type=ListType.BULLET,
            items=tuple(items),
            source=SourceSpan(
                line_start=start_index + 1,
                line_end=line_end + 1,
                filename=filename,
            ),
        ),
        line_end,
    )


def _parse_indented_numeric_list(
    lines: list[str],
    start_index: int,
    filename: str | None,
) -> tuple[ListNode, int]:
    items: list[ListItemNode] = []
    i = start_index
    base_indent: int | None = None
    while i < len(lines):
        match = _INDENTED_NUMERIC_ITEM_RE.match(lines[i])
        if match is None:
            break
        indent = len(match.group(1).replace("\t", "    "))
        if base_indent is None:
            base_indent = indent
        if indent != base_indent:
            break
        items.append(
            ListItemNode(
                text=match.group(3).strip(),
                source=_span_for_line(lines[i], i, filename),
            )
        )
        i += 1

    return (
        ListNode(
            list_type=ListType.NUMBERED,
            items=tuple(items),
            source=SourceSpan(
                line_start=start_index + 1,
                line_end=i,
                filename=filename,
            ),
        ),
        i - 1,
    )


def _is_list_start(stripped: str) -> bool:
    return stripped == "[LIST]" or stripped.startswith("[LIST ")


def _parse_toc_marker(stripped: str, span: SourceSpan) -> TableOfContentsNode:
    attrs = _parse_attributes(stripped)
    title = attrs.get("title", "СОДЕРЖАНИЕ").strip() or "СОДЕРЖАНИЕ"
    levels_value = attrs.get("levels", "3")
    try:
        levels = int(levels_value)
    except (TypeError, ValueError):
        levels = 3
    levels = max(1, min(9, levels))
    return TableOfContentsNode(title=title, levels=levels, source=span)


def _parse_title_page_marker(stripped: str, span: SourceSpan) -> TitlePageNode:
    attrs = _parse_attributes(stripped)
    profile = attrs.get("profile")
    if profile is not None:
        profile = profile.strip() or None
    return TitlePageNode(profile=profile, source=span)


def _parse_metadata_marker(
    stripped: str,
    span: SourceSpan,
    diagnostics: list[Diagnostic],
) -> MetadataNode | None:
    attrs = _parse_attributes(stripped)
    key = (attrs.get("key") or "").strip()
    if not key:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                message="META marker missing required 'key' attribute",
                severity=Severity.ERROR,
                source=span,
            )
        )
        return None
    value = attrs.get("value", "")
    return MetadataNode(key=key, value=value, source=span)


def _collect_metadata(blocks: list) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for block in blocks:
        if isinstance(block, MetadataNode):
            metadata[block.key] = block.value
    return metadata


def _parse_attributes(text: str) -> dict[str, str]:
    return parse_attributes(text)


def _parse_section_marker(
    stripped: str,
    span: SourceSpan,
    diagnostics: list[Diagnostic],
) -> StructuralSectionNode | None:
    attrs = _parse_attributes(stripped)
    section_type_name = attrs.get("type", "").strip().lower()
    section_type = _STRUCTURAL_TYPE_ALIASES.get(section_type_name)
    if section_type is None:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                message=(f"Unknown structural section type: {section_type_name or '<empty>'}"),
                severity=Severity.ERROR,
                source=span,
            )
        )
        return None
    return StructuralSectionNode(
        section_type=section_type,
        title=section_type.value,
        source=span,
    )


def _parse_structural_marker(
    stripped: str,
    span: SourceSpan,
    diagnostics: list[Diagnostic],
) -> StructuralSectionNode | None:
    attrs = _parse_attributes(stripped)
    title = attrs.get("title", "").strip()
    structural = _structural_section_from_title(title, span)
    if structural is None:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                message=f"Unknown structural section title: {title or '<empty>'}",
                severity=Severity.ERROR,
                source=span,
            )
        )
    return structural


def _structural_section_from_title(
    title: str,
    span: SourceSpan,
) -> StructuralSectionNode | None:
    normalized = _normalize_structural_title(title)
    section_type = _STRUCTURAL_SECTIONS_BY_TITLE.get(normalized)
    if section_type is None:
        return None
    return StructuralSectionNode(
        section_type=section_type,
        title=title.strip(),
        source=span,
    )


def _normalize_structural_title(title: str) -> str:
    return " ".join(title.strip().upper().split())


def _caption_after_image(lines: list[str], image_index: int) -> tuple[str | None, int]:
    if image_index + 1 >= len(lines):
        return None, 0
    next_line = lines[image_index + 1].strip()
    if next_line.startswith(SyntaxConfig.FIGURE_CAPTION_PREFIXES):
        return next_line, 1
    return None, 0


def _parse_formula_symbol(stripped: str) -> FormulaSymbol:
    attrs = _parse_attributes(stripped)
    return FormulaSymbol(
        name=attrs.get("name", "").strip(),
        description=attrs.get("text", attrs.get("description", "")).strip(),
        repeats=(attrs.get("repeats", "").strip().casefold() in {"true", "1", "yes", "да"}),
    )


def _formula_content(lines: list[str]) -> str:
    if not lines:
        return ""
    return lines[0].strip("\n")


def _formula_continuation_lines(lines: list[str]) -> tuple[str, ...]:
    return tuple(line.strip("\n") for line in lines[1:])


def _parse_inline_formatting(
    text: str,
    source: SourceSpan | None = None,
    diagnostics: list[Diagnostic] | None = None,
) -> tuple:
    """Split text into TextRuns by ``***bi***``, ``**bold**``, ``*italic*``."""

    return split_citation_runs(
        text,
        source=source,
        diagnostics=diagnostics,
        parse_text=lambda value: _parse_inline_formatting_without_citations(value, source),
    )


def _parse_inline_formatting_without_citations(
    text: str,
    source: SourceSpan | None = None,
) -> tuple[TextRun, ...]:
    """Split text into TextRuns by ``***bi***``, ``**bold**``, ``*italic*``."""

    runs: list[TextRun] = []
    cursor = 0
    for match in _INLINE_FORMATTING_RE.finditer(text):
        start, end = match.span()
        if start > cursor:
            runs.append(TextRun(text=text[cursor:start], source=source))
        bi, bold, italic = match.group(1), match.group(2), match.group(3)
        if bi is not None:
            runs.append(TextRun(text=bi, bold=True, italic=True, source=source))
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
