from __future__ import annotations

import re
from dataclasses import replace

from sfu_converter.domain.ast_nodes import (
    AbbreviationEntryNode,
    AbbreviationsListNode,
    AppendixNode,
    BibliographyEntryNode,
    ContinuationLabel,
    Document,
    DrawingSheetNode,
    FigureNode,
    FootnoteAnchor,
    FootnoteNode,
    FormulaNode,
    FormulaSymbol,
    FrameType,
    HeadingLevel,
    HeadingNode,
    ListItemNode,
    ListNode,
    ListType,
    MetadataNode,
    PageBreakNode,
    ParagraphNode,
    PosterNode,
    ProjectDesignationNode,
    RawBlockNode,
    ReferenceNode,
    SectionOrientation,
    SectionSetupNode,
    SheetFormat,
    SourceSpan,
    SourceRecordNode,
    SourceRecordType,
    SlideDeckNode,
    SlideNode,
    TableNote,
    TableNode,
    TitlePageNode,
    TitleBlockForm,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.parser.attributes import parse_attributes
from sfu_converter.parser.base import BaseParser, ParserResult
from sfu_converter.parser.v1_parser import (
    _EXPLICIT_LIST_ITEM_RE,
    _LIST_TYPE_ALIASES,
    V1Parser,
    _parse_inline_formatting,
    _is_table_separator_row,
    _parse_table_row,
    _parse_structural_marker,
    _span_for_line,
    _structural_section_from_title,
)

_KNOWN_V2_MARKERS = (
    "[APPENDIX",
    "[ABBREVIATIONS",
    "[ABBREVIATIONS_END]",
    "[ABBR",
    "[DOC",
    "[DESIGNATION",
    "[DRAWING",
    "[/DRAWING]",
    "[FIGURE",
    "[FN",
    "[FN_ANCHOR",
    "[FN_BODY",
    "[FORMULA",
    "[FORMULA_END]",
    "[FORMULA_SYMBOL",
    "[H",
    "[LIST",
    "[LIST_END]",
    "[META",
    "[P]",
    "[PAGE_BREAK]",
    "[POSTER",
    "[/POSTER]",
    "[RAW]",
    "[RAW_END]",
    "[REF",
    "[SOURCE",
    "[/SOURCE]",
    "[SECTION",
    "[/SECTION]",
    "[SLIDE",
    "[/SLIDE]",
    "[SLIDE_DECK",
    "[/SLIDE_DECK]",
    "[STRUCTURAL",
    "[TABLE",
    "[TABLE_END]",
    "[TABLE_NOTE",
    "[TITLE_PAGE",
)


class V2Parser(BaseParser):
    """Parser for explicit, line-oriented version 2 TXT syntax."""

    def __init__(self, *, strict: bool = False):
        self.strict = strict
        self._v1_compat = V1Parser()

    def parse(self, source: str, filename: str | None = None) -> ParserResult:
        lines = source.splitlines()
        blocks = []
        diagnostics: list[Diagnostic] = []
        metadata: dict[str, str] = {}
        seen_ids: dict[str, SourceSpan] = {}
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()
            span = _span_for_line(lines[i], i, filename)

            if not stripped:
                i += 1
                continue

            if stripped.startswith("["):
                self._v1_compat._check_cyrillic(stripped, span, diagnostics)

            if stripped.startswith("[DOC"):
                self._parse_doc(stripped, span, metadata, diagnostics)
            elif stripped.startswith("[DESIGNATION"):
                designation = self._parse_designation(stripped, span, diagnostics)
                if designation is not None:
                    blocks.append(designation)
            elif stripped.startswith("[META"):
                metadata_node = self._parse_metadata(stripped, span, diagnostics)
                if metadata_node is not None:
                    metadata[metadata_node.key] = metadata_node.value
                    blocks.append(metadata_node)
            elif stripped.startswith("[TITLE_PAGE"):
                blocks.append(self._parse_title_page(stripped, span))
            elif stripped.startswith("[H "):
                heading = self._parse_heading(stripped, span, diagnostics)
                if heading is not None:
                    structural = _structural_section_from_title(heading.text, span)
                    blocks.append(structural if structural is not None else heading)
            elif _is_paragraph_marker(stripped):
                marker, _, text = stripped.partition("]")
                paragraph_attrs = self._parse_attributes(f"{marker}]")
                paragraph, footnotes = _parse_v2_paragraph(
                    text.strip(),
                    span,
                    diagnostics,
                    metadata=paragraph_attrs,
                )
                blocks.append(paragraph)
                blocks.extend(footnotes)
            elif stripped.startswith("[FIGURE"):
                figure = self._parse_figure(stripped, span)
                self._remember_id(figure.id, span, seen_ids, diagnostics)
                blocks.append(figure)
            elif stripped.startswith("[DRAWING"):
                drawing, drawing_diagnostics, end_index = self._parse_drawing(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(drawing_diagnostics)
                blocks.append(drawing)
                i = end_index
            elif stripped.startswith("[POSTER"):
                poster, poster_diagnostics, end_index = self._parse_poster(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(poster_diagnostics)
                blocks.append(poster)
                i = end_index
            elif stripped.startswith("[SLIDE_DECK"):
                deck, deck_diagnostics, end_index = self._parse_slide_deck(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(deck_diagnostics)
                blocks.append(deck)
                i = end_index
            elif stripped.startswith("[TABLE"):
                table, table_diagnostics, end_index = self._parse_table(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(table_diagnostics)
                if table is not None:
                    self._remember_id(table.id, span, seen_ids, diagnostics)
                    blocks.append(table)
                i = end_index
            elif stripped.startswith("[ABBREVIATIONS"):
                abbreviations, abbreviation_diagnostics, end_index = self._parse_abbreviations(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(abbreviation_diagnostics)
                blocks.append(abbreviations)
                i = end_index
            elif stripped.startswith("[LIST"):
                list_node, list_diagnostics, end_index = self._parse_list(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(list_diagnostics)
                if list_node is not None:
                    blocks.append(list_node)
                i = end_index
            elif stripped.startswith("[FORMULA"):
                formula, formula_diagnostics, end_index = self._parse_formula(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(formula_diagnostics)
                self._remember_id(formula.id, span, seen_ids, diagnostics)
                blocks.append(formula)
                i = end_index
            elif stripped.startswith("[REF"):
                reference = self._parse_reference(stripped, span, diagnostics)
                if reference is not None:
                    blocks.append(reference)
            elif stripped.startswith("[SOURCE"):
                source_node, source_diagnostics, end_index = self._parse_source(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(source_diagnostics)
                if source_node is not None:
                    blocks.append(source_node)
                i = end_index
            elif stripped.startswith("[STRUCTURAL"):
                structural = _parse_structural_marker(stripped, span, diagnostics)
                if structural is not None:
                    blocks.append(structural)
            elif stripped.startswith("[FN_BODY"):
                footnote, footnote_diagnostics, end_index = self._parse_footnote_body(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(footnote_diagnostics)
                if footnote is not None:
                    blocks.append(footnote)
                i = end_index
            elif stripped.startswith("[SECTION"):
                section, section_diagnostics, end_index = self._parse_section_setup(
                    lines,
                    i,
                    filename,
                )
                diagnostics.extend(section_diagnostics)
                blocks.append(section)
                i = end_index
            elif stripped == "[PAGE_BREAK]":
                blocks.append(PageBreakNode(source=span))
            elif stripped.startswith("[APPENDIX"):
                appendix = self._parse_appendix(stripped, span)
                self._remember_id(appendix.id, span, seen_ids, diagnostics)
                blocks.append(appendix)
            elif stripped == "[RAW]":
                raw, raw_diagnostics, end_index = self._parse_raw(lines, i, filename)
                diagnostics.extend(raw_diagnostics)
                blocks.append(raw)
                i = end_index
            elif stripped.startswith("[") and not stripped.startswith(_KNOWN_V2_MARKERS):
                diagnostics.append(self._unknown_marker(stripped, span))
            elif not stripped.startswith("["):
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
                        message=f"Plain text must be wrapped in [P]: {stripped}",
                        severity=Severity.ERROR if self.strict else Severity.WARNING,
                        source=span,
                    )
                )

            i += 1

        document = Document(
            blocks=tuple(blocks),
            syntax_version=2,
            metadata=metadata,
            source_file=filename,
        )
        return ParserResult(document=document, diagnostics=diagnostics)

    def _parse_attributes(self, text: str) -> dict[str, str]:
        return parse_attributes(text)

    def _parse_doc(
        self,
        stripped: str,
        span: SourceSpan,
        metadata: dict[str, str],
        diagnostics: list[Diagnostic],
    ) -> None:
        attrs = self._parse_attributes(stripped)
        syntax = attrs.get("syntax")
        if syntax is not None and syntax != "2":
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_UNSUPPORTED_SYNTAX,
                    message=f"Unsupported V2 DOC syntax version: {syntax}",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
        for key, value in attrs.items():
            if key != "syntax":
                metadata[key] = value

    def _parse_metadata(
        self,
        stripped: str,
        span: SourceSpan,
        diagnostics: list[Diagnostic],
    ) -> MetadataNode | None:
        attrs = self._parse_attributes(stripped)
        key = attrs.get("key", "").strip()
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
        return MetadataNode(key=key, value=attrs.get("value", ""), source=span)

    def _parse_title_page(self, stripped: str, span: SourceSpan) -> TitlePageNode:
        attrs = self._parse_attributes(stripped)
        profile = attrs.get("profile")
        return TitlePageNode(profile=profile.strip() if profile else None, source=span)

    def _parse_designation(
        self,
        stripped: str,
        span: SourceSpan,
        diagnostics: list[Diagnostic],
    ) -> ProjectDesignationNode | None:
        attrs = self._parse_attributes(stripped)
        prefix = attrs.get("prefix", "").strip()
        specialty = attrs.get("specialty", attrs.get("specialty_code", "")).strip()
        document = attrs.get("document", attrs.get("document_code", "")).strip()
        missing = [
            name
            for name, value in (
                ("prefix", prefix),
                ("specialty", specialty),
                ("document", document),
            )
            if not value
        ]
        if missing:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message=f"DESIGNATION marker missing required attributes: {', '.join(missing)}",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None

        schema_code = attrs.get("schema_code")
        schema_type = attrs.get("schema_type")
        schema = attrs.get("schema")
        if schema and schema_code is None and schema_type is None:
            schema_code = schema[:1] or None
            schema_type = schema[1:] or None

        return ProjectDesignationNode(
            prefix=prefix,
            specialty_code=specialty,
            group_code=attrs.get("group", attrs.get("group_code")),
            document_code=document,
            year=attrs.get("year"),
            schema_code=schema_code,
            schema_type=schema_type,
            source=span,
        )

    def _parse_heading(
        self,
        stripped: str,
        span: SourceSpan,
        diagnostics: list[Diagnostic],
    ) -> HeadingNode | None:
        attrs = self._parse_attributes(stripped)
        raw_level = attrs.get("level", "1")
        try:
            level_value = int(raw_level)
        except ValueError:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message=f"Invalid heading level: {raw_level}",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None
        try:
            level = HeadingLevel(level_value)
        except ValueError:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.INVALID_HEADING_LEVEL,
                    message=f"Heading level {level_value} is not allowed (max H4)",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None
        return HeadingNode(
            level=level,
            text=attrs.get("title", ""),
            number=attrs.get("number"),
            source=span,
        )

    def _parse_figure(self, stripped: str, span: SourceSpan) -> FigureNode:
        attrs = self._parse_attributes(stripped)
        return FigureNode(
            src=attrs.get("src"),
            caption=attrs.get("caption"),
            id=attrs.get("id"),
            explanatory_data=_parse_explanatory_data(attrs.get("explanatory")),
            sheet=_parse_optional_int(attrs.get("sheet")),
            total_sheets=_parse_optional_int(attrs.get("total_sheets")),
            source=span,
        )

    def _parse_drawing(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[DrawingSheetNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        attrs = self._parse_attributes(lines[start_index].strip())
        start_span = _span_for_line(lines[start_index], start_index, filename)
        body_attrs: dict[str, str] = {}
        i = start_index + 1
        found_end = False
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped == "[/DRAWING]":
                found_end = True
                break
            if stripped:
                assignment = _parse_assignment_line(stripped)
                if assignment:
                    body_attrs.update(assignment)
                else:
                    diagnostics.append(self._unknown_marker(stripped, _span_for_line(lines[i], i, filename)))
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="DRAWING without matching /DRAWING",
                    severity=Severity.ERROR,
                    source=start_span,
                )
            )

        attrs = {**attrs, **body_attrs}
        end_index = i if found_end else len(lines) - 1
        return (
            DrawingSheetNode(
                sheet_format=_parse_sheet_format(attrs.get("sheet", attrs.get("format"))),
                frame=_parse_frame_type(attrs.get("frame", FrameType.GRAPHIC.value)),
                title_block_form=_parse_title_block_form(attrs.get("form")) or TitleBlockForm.FORM_5,
                scale=attrs.get("scale"),
                src=attrs.get("src"),
                designation=attrs.get("designation"),
                font_type=attrs.get("font", attrs.get("font_type")),
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=end_index + 1,
                    filename=filename,
                ),
            ),
            diagnostics,
            end_index,
        )

    def _parse_poster(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[PosterNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        attrs = self._parse_attributes(lines[start_index].strip())
        start_span = _span_for_line(lines[start_index], start_index, filename)
        body_lines: list[str] = []
        i = start_index + 1
        found_end = False
        while i < len(lines):
            if lines[i].strip() == "[/POSTER]":
                found_end = True
                break
            body_lines.append(lines[i])
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="POSTER without matching /POSTER",
                    severity=Severity.ERROR,
                    source=start_span,
                )
            )

        nested_result = V2Parser(strict=self.strict).parse("\n".join(body_lines), filename=filename)
        diagnostics.extend(nested_result.diagnostics)
        end_index = i if found_end else len(lines) - 1
        return (
            PosterNode(
                sheet_format=_parse_sheet_format(attrs.get("format", attrs.get("sheet"))),
                title=attrs.get("title", ""),
                blocks=nested_result.document.blocks,
                fill_percent=_parse_optional_float(
                    attrs.get("fill", attrs.get("fill_percent", attrs.get("fill_density")))
                ),
                reverse_title_block=not _is_false(attrs.get("reverse_title_block")),
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=end_index + 1,
                    filename=filename,
                ),
            ),
            diagnostics,
            end_index,
        )

    def _parse_slide_deck(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[SlideDeckNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        attrs = self._parse_attributes(lines[start_index].strip())
        start_span = _span_for_line(lines[start_index], start_index, filename)
        slides: list[SlideNode] = []
        i = start_index + 1
        found_end = False
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped == "[/SLIDE_DECK]":
                found_end = True
                break
            if stripped.startswith("[SLIDE"):
                slide, slide_diagnostics, end_index = self._parse_slide(lines, i, filename)
                diagnostics.extend(slide_diagnostics)
                slides.append(slide)
                i = end_index + 1
                continue
            if stripped:
                diagnostics.append(self._unknown_marker(stripped, _span_for_line(lines[i], i, filename)))
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="SLIDE_DECK without matching /SLIDE_DECK",
                    severity=Severity.ERROR,
                    source=start_span,
                )
            )

        end_index = i if found_end else len(lines) - 1
        return (
            SlideDeckNode(
                sheet_format=_parse_sheet_format(attrs.get("format", attrs.get("sheet"))),
                slides=tuple(slides),
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=end_index + 1,
                    filename=filename,
                ),
            ),
            diagnostics,
            end_index,
        )

    def _parse_slide(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[SlideNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        stripped = lines[start_index].strip()
        span = _span_for_line(lines[start_index], start_index, filename)
        marker, _, trailing = stripped.partition("]")
        attrs = self._parse_attributes(f"{marker}]")
        fields = _slide_fields(attrs)
        body: list[str] = []

        inline_body, inline_end, _ = trailing.partition("[/SLIDE]")
        if inline_end:
            if inline_body.strip():
                body.append(inline_body.strip())
            return (
                _make_slide(attrs, fields, body, span),
                diagnostics,
                start_index,
            )

        if trailing.strip():
            body.append(trailing.strip())
        i = start_index + 1
        found_end = False
        while i < len(lines):
            body_line = lines[i].strip()
            if body_line == "[/SLIDE]":
                found_end = True
                break
            assignment = _parse_assignment_line(body_line)
            if assignment:
                fields.update(assignment)
            elif body_line:
                body.append(body_line)
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="SLIDE without matching /SLIDE",
                    severity=Severity.ERROR,
                    source=span,
                )
            )

        end_index = i if found_end else len(lines) - 1
        slide = _make_slide(
            attrs,
            fields,
            body,
            SourceSpan(
                line_start=span.line_start,
                line_end=end_index + 1,
                filename=filename,
            ),
        )
        return slide, diagnostics, end_index

    def _parse_table(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[TableNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        attrs = self._parse_attributes(lines[start_index].strip())
        rows = []
        notes: list[TableNote] = []
        expected_cell_count: int | None = None
        table_start_span = _span_for_line(lines[start_index], start_index, filename)
        i = start_index + 1
        found_end = False

        while i < len(lines):
            stripped = lines[i].strip()
            span = _span_for_line(lines[i], i, filename)
            if stripped.startswith("["):
                self._v1_compat._check_cyrillic(stripped, span, diagnostics)
            if stripped.startswith("[TABLE_END]"):
                found_end = True
                break
            if stripped.startswith("[TABLE_NOTE"):
                note = self._parse_table_note(stripped, span)
                notes.append(note)
                i += 1
                continue
            if stripped.startswith("|"):
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
            elif stripped:
                diagnostics.append(self._unknown_marker(stripped, span))
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="TABLE without matching TABLE_END",
                    severity=Severity.ERROR,
                    source=table_start_span,
                )
            )

        if not rows:
            return None, diagnostics, i

        header_row_count = _parse_int(attrs.get("header_rows"), default=-1)
        if header_row_count < 0:
            header_row_count = 0 if attrs.get("header", "true").lower() == "false" else 1
        return (
            TableNode(
                rows=tuple(rows),
                caption=attrs.get("caption"),
                id=attrs.get("id"),
                number=attrs.get("number"),
                unit_label=attrs.get("unit"),
                continuation=_parse_continuation(attrs.get("continuation")),
                notes=tuple(notes),
                column_units=_parse_column_units(attrs.get("column_units")),
                header_row_count=header_row_count,
                source=SourceSpan(
                    line_start=table_start_span.line_start,
                    line_end=i + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _parse_table_note(self, stripped: str, span: SourceSpan) -> TableNote:
        attrs = self._parse_attributes(stripped)
        return TableNote(
            marker=attrs.get("marker", "*"),
            text=attrs.get("text", ""),
            source=span,
        )

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
                attrs = self._parse_attributes(stripped)
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
                diagnostics.append(self._unknown_marker(stripped, span))
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="ABBREVIATIONS without matching ABBREVIATIONS_END",
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

    def _parse_list(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[ListNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        attrs = self._parse_attributes(lines[start_index].strip())
        list_start_span = _span_for_line(lines[start_index], start_index, filename)
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
            if stripped.startswith("[LIST_END]"):
                found_end = True
                break
            if stripped.startswith("[LIST"):
                nested, nested_diagnostics, nested_end = self._parse_list(lines, i, filename)
                diagnostics.extend(nested_diagnostics)
                if nested is not None and items:
                    last_item = items[-1]
                    items[-1] = replace(last_item, children=(*last_item.children, nested))
                elif nested is not None:
                    diagnostics.append(
                        Diagnostic(
                            code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                            message="Nested LIST must follow a list item",
                            severity=Severity.ERROR,
                            source=span,
                        )
                    )
                i = nested_end + 1
                continue
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

        return (
            ListNode(
                list_type=list_type or ListType.BULLET,
                items=tuple(items),
                source=SourceSpan(
                    line_start=list_start_span.line_start,
                    line_end=i + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _parse_formula(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[FormulaNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        attrs = self._parse_attributes(lines[start_index].strip())
        start_span = _span_for_line(lines[start_index], start_index, filename)
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
                    source=start_span,
                )
            )

        explanation = None
        end_index = i
        next_index = i + 1
        if next_index < len(lines):
            next_line = lines[next_index].strip()
            if next_line.startswith("[FORMULA_EXPLANATION]"):
                explanation = next_line.replace("[FORMULA_EXPLANATION]", "", 1).strip()
                end_index = next_index

        return (
            FormulaNode(
                content=_formula_content(formula_lines),
                id=attrs.get("id"),
                number=attrs.get("number"),
                format=attrs.get("format"),
                explanation=explanation,
                explanations=tuple(explanations),
                continuation_lines=_formula_continuation_lines(formula_lines),
                consecutive_with=_parse_consecutive_with(attrs),
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=end_index + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            end_index,
        )

    def _parse_reference(
        self,
        stripped: str,
        span: SourceSpan,
        diagnostics: list[Diagnostic],
    ) -> ReferenceNode | None:
        attrs = self._parse_attributes(stripped)
        target = attrs.get("target", "").strip()
        if not target:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message="REF marker missing required 'target' attribute",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None
        return ReferenceNode(target=target, source=span)

    def _parse_source(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[BibliographyEntryNode | SourceRecordNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        stripped = lines[start_index].strip()
        span = _span_for_line(lines[start_index], start_index, filename)
        marker, _, text = stripped.partition("]")
        attrs = self._parse_attributes(f"{marker}]")
        try:
            number = int(attrs.get("number", ""))
        except ValueError:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message=f"Invalid SOURCE number: {attrs.get('number', '<missing>')}",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None, diagnostics, start_index

        record_type = attrs.get("type")
        if record_type is None:
            return BibliographyEntryNode(number=number, text=text.strip(), source=span), diagnostics, start_index

        try:
            source_record_type = SourceRecordType(record_type)
        except ValueError:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message=f"Unknown SOURCE type: {record_type}",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None, diagnostics, start_index

        fields: dict[str, str] = {}
        i = start_index + 1
        found_end = False
        while i < len(lines):
            body_line = lines[i].strip()
            if body_line == "[/SOURCE]":
                found_end = True
                break
            fields.update(parse_attributes(body_line))
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="SOURCE without matching /SOURCE",
                    severity=Severity.ERROR,
                    source=span,
                )
            )

        return (
            SourceRecordNode(
                number=number,
                record_type=source_record_type,
                fields=fields,
                language=attrs.get("lang", attrs.get("language", "ru")),
                source=SourceSpan(
                    line_start=span.line_start,
                    line_end=i + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _parse_section_setup(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[SectionSetupNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        stripped = lines[start_index].strip()
        start_span = _span_for_line(lines[start_index], start_index, filename)
        attrs = self._parse_attributes(stripped)

        body_lines: list[str] = []
        i = start_index + 1
        found_end = False
        while i < len(lines):
            if lines[i].strip() == "[/SECTION]":
                found_end = True
                break
            body_lines.append(lines[i])
            i += 1

        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="SECTION without matching /SECTION",
                    severity=Severity.ERROR,
                    source=start_span,
                )
            )

        nested_result = V2Parser(strict=self.strict).parse("\n".join(body_lines), filename=filename)
        diagnostics.extend(nested_result.diagnostics)
        end_index = i if found_end else len(lines) - 1
        return (
            SectionSetupNode(
                orientation=_parse_section_orientation(attrs.get("orientation")),
                sheet_format=_parse_sheet_format(attrs.get("sheet")),
                frame=_parse_frame_type(attrs.get("frame")),
                title_block_form=_parse_title_block_form(attrs.get("form")),
                blocks=nested_result.document.blocks,
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=end_index + 1,
                    filename=filename,
                ),
            ),
            diagnostics,
            end_index,
        )

    def _parse_footnote_body(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[FootnoteNode | None, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        stripped = lines[start_index].strip()
        span = _span_for_line(lines[start_index], start_index, filename)
        marker, _, trailing = stripped.partition("]")
        attrs = self._parse_attributes(f"{marker}]")
        marker_id = attrs.get("id", "").strip()
        if not marker_id:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE,
                    message="FN_BODY marker missing required 'id' attribute",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
            return None, diagnostics, start_index

        text_parts: list[str] = []
        end_inline = trailing.partition("[/FN_BODY]")
        if end_inline[1]:
            text_parts.append(end_inline[0].strip())
            return FootnoteNode(marker=marker_id, text="\n".join(text_parts), source=span), diagnostics, start_index

        if trailing.strip():
            text_parts.append(trailing.strip())
        i = start_index + 1
        found_end = False
        while i < len(lines):
            body_line = lines[i]
            if body_line.strip() == "[/FN_BODY]":
                found_end = True
                break
            text_parts.append(body_line)
            i += 1
        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="FN_BODY without matching /FN_BODY",
                    severity=Severity.ERROR,
                    source=span,
                )
            )
        return (
            FootnoteNode(
                marker=marker_id,
                text="\n".join(text_parts).strip(),
                source=SourceSpan(
                    line_start=span.line_start,
                    line_end=i + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _parse_appendix(self, stripped: str, span: SourceSpan) -> AppendixNode:
        attrs = self._parse_attributes(stripped)
        return AppendixNode(
            title=attrs.get("title", "ПРИЛОЖЕНИЕ"),
            id=attrs.get("id"),
            letter=attrs.get("letter"),
            appendix_type=attrs.get("type"),
            subtitle=attrs.get("subtitle"),
            sheet_format=_parse_sheet_format(attrs.get("sheet", attrs.get("format"))),
            independent=_parse_bool(attrs.get("independent")),
            source=span,
        )

    def _parse_raw(
        self,
        lines: list[str],
        start_index: int,
        filename: str | None,
    ) -> tuple[RawBlockNode, list[Diagnostic], int]:
        diagnostics: list[Diagnostic] = []
        raw_lines: list[str] = []
        start_span = _span_for_line(lines[start_index], start_index, filename)
        i = start_index + 1
        found_end = False
        while i < len(lines):
            if lines[i].strip() == "[RAW_END]":
                found_end = True
                break
            raw_lines.append(lines[i])
            i += 1
        if not found_end:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_MISSING_BLOCK_END,
                    message="RAW without matching RAW_END",
                    severity=Severity.ERROR,
                    source=start_span,
                )
            )
        return (
            RawBlockNode(
                text="\n".join(raw_lines),
                source=SourceSpan(
                    line_start=start_span.line_start,
                    line_end=i + 1 if found_end else len(lines),
                    filename=filename,
                ),
            ),
            diagnostics,
            i,
        )

    def _remember_id(
        self,
        identifier: str | None,
        span: SourceSpan,
        seen_ids: dict[str, SourceSpan],
        diagnostics: list[Diagnostic],
    ) -> None:
        if not identifier:
            return
        if identifier in seen_ids:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.TXT_DUPLICATE_ID,
                    message=f"Duplicate id: {identifier}",
                    severity=Severity.ERROR,
                    source=span,
                    suggestion="Use a unique id for every referenceable block",
                )
            )
            return
        seen_ids[identifier] = span

    def _unknown_marker(self, stripped: str, span: SourceSpan) -> Diagnostic:
        return Diagnostic(
            code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
            message=f"Unknown marker: {stripped}",
            severity=Severity.ERROR if self.strict else Severity.WARNING,
            source=span,
        )


def _parse_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"true", "1", "yes", "да"}


def _is_false(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"false", "0", "no", "нет"}


def _parse_optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_assignment_line(stripped: str) -> dict[str, str]:
    if "=" not in stripped or stripped.startswith("["):
        return {}
    key, _, value = stripped.partition("=")
    key = key.strip()
    if not key or not key.replace("_", "").isalnum():
        return {}
    return {key: value.strip().strip('"')}


def _slide_fields(attrs: dict[str, str]) -> dict[str, str]:
    excluded = {"first_slide", "fill", "fill_percent", "fill_density"}
    return {key: value for key, value in attrs.items() if key not in excluded}


def _make_slide(
    attrs: dict[str, str],
    fields: dict[str, str],
    body: list[str],
    source: SourceSpan,
) -> SlideNode:
    return SlideNode(
        first_slide=_parse_bool(attrs.get("first_slide")),
        fields=fields,
        body=tuple(body),
        fill_percent=_parse_optional_float(
            attrs.get("fill", attrs.get("fill_percent", attrs.get("fill_density")))
        ),
        source=source,
    )


def _is_paragraph_marker(stripped: str) -> bool:
    return stripped.startswith("[P]") or stripped.startswith("[P ")


_FOOTNOTE_INLINE_RE = re.compile(r"\[(FN|FN_ANCHOR)\b[^\]]*\]")


def _parse_v2_paragraph(
    text: str,
    span: SourceSpan,
    diagnostics: list[Diagnostic] | None = None,
    metadata: dict[str, str] | None = None,
) -> tuple[ParagraphNode, tuple[FootnoteNode, ...]]:
    runs = []
    footnotes: list[FootnoteNode] = []
    cursor = 0
    for match in _FOOTNOTE_INLINE_RE.finditer(text):
        if match.start() > cursor:
            runs.extend(_parse_inline_formatting(text[cursor : match.start()], span, diagnostics))
        attrs = parse_attributes(match.group(0))
        marker = attrs.get("id", "").strip()
        if marker:
            runs.append(FootnoteAnchor(marker=marker, source=span))
            if match.group(1) == "FN":
                footnotes.append(
                    FootnoteNode(
                        marker=marker,
                        text=attrs.get("text", ""),
                        source=span,
                    )
                )
        cursor = match.end()
    if cursor < len(text):
        runs.extend(_parse_inline_formatting(text[cursor:], span, diagnostics))
    return ParagraphNode(runs=tuple(runs), source=span, metadata=metadata or {}), tuple(footnotes)


def _parse_explanatory_data(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    lines = [line.strip() for line in value.replace("\\n", "\n").splitlines()]
    data = tuple(line for line in lines if line)
    return data or None


def _parse_formula_symbol(stripped: str) -> FormulaSymbol:
    attrs = parse_attributes(stripped)
    return FormulaSymbol(
        name=attrs.get("name", "").strip(),
        description=attrs.get("text", attrs.get("description", "")).strip(),
        repeats=_parse_bool(attrs.get("repeats")),
    )


def _formula_content(lines: list[str]) -> str:
    if not lines:
        return ""
    return lines[0].strip("\n")


def _formula_continuation_lines(lines: list[str]) -> tuple[str, ...]:
    return tuple(line.strip("\n") for line in lines[1:])


def _parse_consecutive_with(attrs: dict[str, str]) -> str | None:
    if attrs.get("consecutive_with"):
        return attrs["consecutive_with"]
    consecutive = attrs.get("consecutive")
    if consecutive and consecutive.casefold() not in {"false", "0", "no", "нет"}:
        return None if consecutive.casefold() in {"true", "1", "yes", "да"} else consecutive
    return None


def _parse_continuation(value: str | None) -> ContinuationLabel | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized in {"continuation", "continue", "продолжение"}:
        return ContinuationLabel.CONTINUATION
    if normalized in {"final", "ending", "окончание"}:
        return ContinuationLabel.FINAL
    return None


def _parse_column_units(value: str | None) -> tuple[str | None, ...]:
    if value is None:
        return ()
    units = []
    for item in value.split(","):
        unit = item.strip()
        units.append(None if unit in {"", "-"} else unit)
    return tuple(units)


def _parse_section_orientation(value: str | None) -> SectionOrientation:
    normalized = (value or SectionOrientation.PORTRAIT.value).strip().casefold()
    for orientation in SectionOrientation:
        if normalized == orientation.value:
            return orientation
    return SectionOrientation.PORTRAIT


def _parse_sheet_format(value: str | None) -> SheetFormat:
    normalized = (value or SheetFormat.A4.value).strip().replace("×", "x").casefold()
    for sheet_format in SheetFormat:
        if normalized == sheet_format.value.casefold():
            return sheet_format
    return SheetFormat.A4


def _parse_frame_type(value: str | None) -> FrameType:
    normalized = (value or FrameType.NONE.value).strip().casefold()
    for frame_type in FrameType:
        if normalized == frame_type.value:
            return frame_type
    return FrameType.NONE


def _parse_title_block_form(value: str | None) -> TitleBlockForm | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    for form in TitleBlockForm:
        if normalized == form.value:
            return form
    return None
