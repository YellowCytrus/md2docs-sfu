from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    BibliographyEntryNode,
    FormulaNode,
    HeadingNode,
    ListNode,
    MetadataNode,
    ParagraphNode,
    StructuralSectionNode,
    TableNode,
    TextRun,
    TitlePageNode,
)
from sfu_converter.domain.diagnostics import DiagnosticCodes, Severity
from sfu_converter.parser.v1_parser import (
    V1Parser,
    _caption_after_image,
    _parse_inline_formatting,
    _parse_table_row,
    _span_for_line,
)
from sfu_converter.parser.v2_parser import V2Parser


def _codes(result):
    return [diagnostic.code for diagnostic in result.diagnostics]


def test_v1_parser_covers_malformed_markers_and_blocks():
    source = "\n".join(
        [
            "[Н1] bad cyrillic marker",
            "[IMAGE bad]",
            "[SECTION type=unknown]",
            "[STRUCTURAL title=unknown]",
            "[META value=missing-key]",
            "[FORMULA_END]",
            "[UNKNOWN]",
            "[LIST_END]",
            "[TABLE_CAPTION] Standalone",
            "[TABLE_START]",
            "[TABLE_CAPTION] Data",
            "| A | B |",
            "| C |",
            "[H1] Known marker ignored inside table",
            "[BAD_IN_TABLE]",
            "[TABLE_END]",
            "[TABLE_START]",
            "[TABLE_END]",
            "[LIST type=bad]",
            "[LIST]",
            "bad item",
            "",
            "[LIST_END]",
            "[LIST]",
            "[-] closed item",
            "[LIST_END]",
            "[FORMULA id=f1 number=auto]",
            "x = y",
            "[FORMULA_END]",
            "[H1] СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
            "1 Source title",
            "not numbered source",
            "[H1] ПРИЛОЖЕНИЕ Ё",
            "[H1] ПРИЛОЖЕНИЕ А",
            "Subtitle without type",
            "[H1] ПРИЛОЖЕНИЕ",
            "[H1] ПРИЛОЖЕНИЕ Б",
            "",
            "[H1] ПРИЛОЖЕНИЕ В",
            "",
            "справочное",
            "",
            "Subtitle after type",
            "[H1] ПРИЛОЖЕНИЕ Г",
            "",
            "справочное",
            "",
            "[TOC title=\"\" levels=bad]",
            "[TOC levels=99]",
            "[TITLE_PAGE profile=\"\"]",
            "- dash one",
            "- dash two",
        ]
    )

    result = V1Parser().parse(source, filename="edge-v1.txt")
    missing_results = [
        V1Parser().parse("[LIST]\n[-] missing end"),
        V1Parser().parse("[FORMULA]\nx\n\n[FORMULA_EXPLANATION]\nwhere"),
        V1Parser().parse("[FORMULA]\nx\n[FORMULA_END]\n\n[FORMULA_EXPLANATION]\nwhere"),
        V1Parser().parse("[TABLE_START]\n| A |"),
        V1Parser().parse("[H1] ПРИЛОЖЕНИЕ Б\n\n"),
        V1Parser().parse("[H1] ПРИЛОЖЕНИЕ В\nсправочное\n\n"),
    ]
    codes = _codes(result)
    for missing_result in missing_results:
        codes.extend(_codes(missing_result))
    blocks = result.document.blocks

    assert DiagnosticCodes.TXT_CYRILLIC_IN_MARKER in codes
    assert DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE in codes
    assert DiagnosticCodes.TXT_UNKNOWN_MARKER in codes
    assert DiagnosticCodes.TXT_INVALID_TABLE_SHAPE in codes
    assert DiagnosticCodes.TXT_MISSING_BLOCK_END in codes
    assert any(isinstance(block, TableNode) for block in blocks)
    assert any(isinstance(block, ListNode) for block in blocks)
    assert any(isinstance(block, FormulaNode) and block.id == "f1" for block in blocks)
    assert any(isinstance(block, BibliographyEntryNode) for block in blocks)
    assert any(isinstance(block, ParagraphNode) and block.runs[0].text == "not numbered source" for block in blocks)
    assert any(isinstance(block, HeadingNode) and block.text == "ПРИЛОЖЕНИЕ Ё" for block in blocks)
    assert any(isinstance(block, AppendixNode) and block.letter == "А" for block in blocks)
    assert any(isinstance(block, TitlePageNode) and block.profile is None for block in blocks)


def test_v1_parser_helper_edge_cases():
    assert _parse_table_row("not a table") is None
    assert _caption_after_image(["[IMAGE=x.png]"], 0) == (None, 0)
    assert _caption_after_image(["[IMAGE=x.png]", "Not a caption"], 0) == (None, 0)
    assert _parse_inline_formatting("") == (TextRun(text=""),)

    span = _span_for_line("", 0, "empty.txt")
    assert span.col_start == 0
    assert span.filename == "empty.txt"


def test_v2_parser_covers_invalid_and_optional_paths():
    source = "\n".join(
        [
            "",
            "[DОC syntax=2]",
            "[DOC syntax=3 profile=common]",
            "[META value=missing-key]",
            '[H level=bad title="Broken"]',
            '[H level=1 title="ВВЕДЕНИЕ"]',
            "[P] **bold** and *italic*",
            '[FIGURE src="a.png" id=dup]',
            '[FIGURE src="b.png" id=dup]',
            '[TABLE id=dup header=false caption="Data"]',
            "| A | B |",
            "| C |",
            "",
            "bad row",
            "[TABLE_END]",
            '[TABLE caption="No rows"]',
            "[TABLE_END]",
            "[LIST type=bad]",
            "[LIST type=bullet]",
            "bad item",
            "",
            "[LIST_END]",
            "[LIST type=bullet]",
            "[-] closed item",
            "[LIST_END]",
            "[FORMULA id=eq:ok number=auto]",
            "a = b",
            "[FORMULA_END]",
            "[FORMULA_EXPLANATION] where a is b",
            "[REF]",
            "[REF target=fig:ok]",
            "[SOURCE number=bad] Bad",
            "[SOURCE number=1] Good",
            "[PAGE_BREAK]",
            '[APPENDIX id=app:a title="Appendix A"]',
            "[RAW]",
            "[literal marker]",
            "[RAW_END]",
            "[RAW_END]",
            "[UNKNOWN]",
            "plain text",
        ]
    )

    result = V2Parser(strict=True).parse(source, filename="edge-v2.txt")
    missing_results = [
        V2Parser(strict=True).parse("[TABLE]\n| A |"),
        V2Parser(strict=True).parse("[LIST type=bullet]\n[-] missing end"),
        V2Parser(strict=True).parse("[FORMULA id=eq:missing]\nx = y"),
        V2Parser(strict=True).parse("[RAW]\nunterminated"),
    ]
    codes = _codes(result)
    for missing_result in missing_results:
        codes.extend(_codes(missing_result))
    blocks = result.document.blocks

    assert DiagnosticCodes.TXT_CYRILLIC_IN_MARKER in codes
    assert DiagnosticCodes.TXT_UNSUPPORTED_SYNTAX in codes
    assert DiagnosticCodes.TXT_MALFORMED_ATTRIBUTE in codes
    assert DiagnosticCodes.TXT_INVALID_TABLE_SHAPE in codes
    assert DiagnosticCodes.TXT_MISSING_BLOCK_END in codes
    assert DiagnosticCodes.TXT_DUPLICATE_ID in codes
    assert DiagnosticCodes.TXT_UNKNOWN_MARKER in codes
    assert all(
        diagnostic.severity is Severity.ERROR
        for diagnostic in result.diagnostics
        if diagnostic.code == DiagnosticCodes.TXT_UNKNOWN_MARKER
    )
    assert result.document.metadata["profile"] == "common"
    assert any(isinstance(block, StructuralSectionNode) for block in blocks)
    assert any(isinstance(block, MetadataNode) for block in blocks) is False
    assert any(isinstance(block, TableNode) and block.header_row_count == 0 for block in blocks)
    assert any(isinstance(block, FormulaNode) and block.explanation == "where a is b" for block in blocks)


def test_v2_parser_non_strict_plain_text_is_warning():
    result = V2Parser(strict=False).parse("plain")

    assert result.diagnostics[0].code == DiagnosticCodes.TXT_UNKNOWN_MARKER
    assert result.diagnostics[0].severity is Severity.WARNING
