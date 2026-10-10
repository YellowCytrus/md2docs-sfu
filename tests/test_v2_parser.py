import pytest

from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    BibliographyEntryNode,
    FigureNode,
    FormulaNode,
    FormulaSymbol,
    FrameType,
    HeadingLevel,
    HeadingNode,
    ListNode,
    ListType,
    MetadataNode,
    PageBreakNode,
    ParagraphNode,
    RawBlockNode,
    ReferenceNode,
    SectionOrientation,
    SectionSetupNode,
    SheetFormat,
    StructuralSectionNode,
    StructuralSectionType,
    TableNode,
    TitleBlockForm,
)
from sfu_converter.domain.diagnostics import DiagnosticCodes, Severity
from sfu_converter.parser import V1Parser, V2Parser, get_parser


def _block_summary(document):
    summary = []
    for block in document.blocks:
        if isinstance(block, HeadingNode):
            summary.append(("heading", block.level, block.text, block.number))
        elif isinstance(block, ParagraphNode):
            summary.append(("paragraph", "".join(run.text for run in block.runs)))
        elif isinstance(block, FigureNode):
            summary.append(("figure", block.src, block.caption, block.id))
        elif isinstance(block, TableNode):
            summary.append(
                (
                    "table",
                    block.caption,
                    block.id,
                    tuple(tuple(cell.text for cell in row.cells) for row in block.rows),
                )
            )
        elif isinstance(block, ListNode):
            summary.append(
                ("list", block.list_type, tuple(item.text for item in block.items))
            )
        elif isinstance(block, FormulaNode):
            summary.append(
                ("formula", block.content, block.id, block.number, block.explanation)
            )
        else:
            summary.append((type(block).__name__,))
    return summary


def test_v2_parser_parses_all_declared_block_types_and_metadata():
    source = "\n".join(
        [
            "[DOC syntax=2 profile=lab_practical_project_reports language=ru]",
            '[META key=title value="Report title"]',
            '[H level=1 title="Chapter" number=auto]',
            "[P] Text **bold** and *italic*.",
            '[FIGURE src="image.png" caption="Description" id=fig:overview number=auto]',
            '[TABLE caption="Data" id=tbl:data number=auto]',
            "| A | B |",
            "| C | D |",
            "[TABLE_END]",
            "[LIST type=bullet]",
            "[-] item 1",
            "[-] item 2",
            "[LIST_END]",
            "[FORMULA id=eq:main number=auto]",
            "E = mc^2",
            "[FORMULA_END]",
            "[REF target=fig:overview]",
            "[SOURCE number=1] Author. Title. Year.",
            "[PAGE_BREAK]",
            '[APPENDIX id=app:a title="Data"]',
            "[RAW]",
            "[This is not a marker]",
            "[RAW_END]",
        ]
    )

    result = V2Parser().parse(source, filename="v2.txt")

    assert result.diagnostics == []
    assert result.document.syntax_version == 2
    assert result.document.source_file == "v2.txt"
    assert dict(result.document.metadata) == {
        "profile": "lab_practical_project_reports",
        "language": "ru",
        "title": "Report title",
    }

    blocks = result.document.blocks
    assert [type(block) for block in blocks] == [
        MetadataNode,
        HeadingNode,
        ParagraphNode,
        FigureNode,
        TableNode,
        ListNode,
        FormulaNode,
        ReferenceNode,
        BibliographyEntryNode,
        PageBreakNode,
        AppendixNode,
        RawBlockNode,
    ]
    assert blocks[1].level is HeadingLevel.H1
    assert blocks[1].number == "auto"
    assert [(run.text, run.bold, run.italic) for run in blocks[2].runs] == [
        ("Text ", False, False),
        ("bold", True, False),
        (" and ", False, False),
        ("italic", False, True),
        (".", False, False),
    ]
    assert blocks[3].id == "fig:overview"
    assert blocks[4].caption == "Data"
    assert blocks[4].id == "tbl:data"
    assert blocks[4].rows[1].cells[1].text == "D"
    assert blocks[5].list_type is ListType.BULLET
    assert [item.text for item in blocks[5].items] == ["item 1", "item 2"]
    assert blocks[6].content == "E = mc^2"
    assert blocks[6].id == "eq:main"
    assert blocks[7].target == "fig:overview"
    assert blocks[8].number == 1
    assert blocks[11].text == "[This is not a marker]"


def test_v2_parser_produces_equivalent_ast_to_v1_for_equivalent_content():
    v1_source = "\n".join(
        [
            "[H1] Chapter",
            "Body text",
            "[IMAGE=image.png]",
            "Рисунок 1 - Description",
            "[TABLE_START]",
            "[TABLE_CAPTION] Data",
            "| A | B |",
            "| C | D |",
            "[TABLE_END]",
            "[LIST type=bullet]",
            "[-] item 1",
            "[-] item 2",
            "[LIST_END]",
            "[FORMULA id=eq:main number=auto]",
            "E = mc^2",
            "[FORMULA_END]",
        ]
    )
    v2_source = "\n".join(
        [
            "[DOC syntax=2]",
            '[H level=1 title="Chapter" number=auto]',
            "[P] Body text",
            '[FIGURE src="image.png" caption="Рисунок 1 - Description"]',
            '[TABLE caption="Data"]',
            "| A | B |",
            "| C | D |",
            "[TABLE_END]",
            "[LIST type=bullet]",
            "[-] item 1",
            "[-] item 2",
            "[LIST_END]",
            "[FORMULA id=eq:main number=auto]",
            "E = mc^2",
            "[FORMULA_END]",
        ]
    )

    v1_result = V1Parser().parse(v1_source)
    v2_result = V2Parser().parse(v2_source)

    assert v1_result.diagnostics == []
    assert v2_result.diagnostics == []
    assert _block_summary(v2_result.document) == _block_summary(v1_result.document)


def test_v2_parser_accepts_structural_section_marker_for_special_titles():
    source = "\n".join(
        [
            '[STRUCTURAL title="ВВЕДЕНИЕ"]',
            '[STRUCTURAL title="СПИСОК ИСТОЧНИКОВ"]',
        ]
    )

    result = V2Parser(strict=True).parse(source)

    assert result.diagnostics == []
    blocks = result.document.blocks
    assert len(blocks) == 2
    assert isinstance(blocks[0], StructuralSectionNode)
    assert isinstance(blocks[1], StructuralSectionNode)
    assert blocks[0].section_type is StructuralSectionType.INTRODUCTION
    assert blocks[0].title == "ВВЕДЕНИЕ"
    assert blocks[1].section_type is StructuralSectionType.SOURCES
    assert blocks[1].title == "СПИСОК ИСТОЧНИКОВ"


def test_v2_parser_parses_figure_explanatory_and_sheet_attributes():
    result = V2Parser().parse(
        '[FIGURE id=f1 src="diagram.png" caption="Архитектура" '
        'explanatory="1 — ввод\\n2 — обработка" sheet=2 total_sheets=3]'
    )

    assert result.diagnostics == []
    (figure,) = result.document.blocks
    assert figure.explanatory_data == ("1 — ввод", "2 — обработка")
    assert figure.sheet == 2
    assert figure.total_sheets == 3


def test_v2_parser_parses_formula_symbols_and_consecutive_with():
    result = V2Parser().parse(
        "\n".join(
            [
                "[FORMULA id=f2 number=auto consecutive_with=f1]",
                "p = m * c",
                '[FORMULA_SYMBOL name=m text="масса, кг"]',
                '[FORMULA_SYMBOL name=c text="" repeats=true]',
                "[FORMULA_END]",
            ]
        )
    )

    assert result.diagnostics == []
    (formula,) = result.document.blocks
    assert formula.consecutive_with == "f1"
    assert formula.explanations == (
        FormulaSymbol(name="m", description="масса, кг"),
        FormulaSymbol(name="c", description="", repeats=True),
    )


def test_v2_parser_accepts_heading_level_four():
    result = V2Parser().parse('[H level=4 title="Sub" number=auto]')

    assert result.diagnostics == []
    heading = result.document.blocks[0]
    assert isinstance(heading, HeadingNode)
    assert heading.level is HeadingLevel.H4
    assert heading.text == "Sub"


def test_v2_parser_rejects_heading_level_above_four():
    result = V2Parser().parse('[H level=5 title="Too deep"]')

    assert result.document.blocks == ()
    codes = [diagnostic.code for diagnostic in result.diagnostics]
    assert DiagnosticCodes.INVALID_HEADING_LEVEL in codes


def test_v2_attribute_parser_supports_quoted_values_with_spaces():
    attrs = V2Parser()._parse_attributes(
        '[META key=title value="A title with spaces" language=ru]'
    )

    assert attrs == {
        "key": "title",
        "value": "A title with spaces",
        "language": "ru",
    }


def test_get_parser_selects_supported_versions_and_rejects_unknown_versions():
    assert isinstance(get_parser(), V2Parser)
    assert isinstance(get_parser(1), V1Parser)
    assert isinstance(get_parser(2), V2Parser)

    with pytest.raises(ValueError, match="Unsupported syntax version"):
        get_parser(3)


def test_v2_unknown_marker_is_warning_by_default_and_error_in_strict_mode():
    default_result = V2Parser().parse("[UNKNOWN]")
    strict_result = V2Parser(strict=True).parse("[UNKNOWN]")

    assert default_result.diagnostics[0].code == DiagnosticCodes.TXT_UNKNOWN_MARKER
    assert default_result.diagnostics[0].severity is Severity.WARNING
    assert strict_result.diagnostics[0].code == DiagnosticCodes.TXT_UNKNOWN_MARKER
    assert strict_result.diagnostics[0].severity is Severity.ERROR
    assert strict_result.has_errors is True


def test_v2_parser_reports_duplicate_ids_and_invalid_doc_syntax():
    duplicate_result = V2Parser().parse(
        "\n".join(
            [
                "[DOC syntax=2]",
                '[FIGURE src="a.png" id=dup]',
                '[TABLE id=dup]',
                "| A |",
                "[TABLE_END]",
            ]
        )
    )
    invalid_syntax_result = V2Parser().parse("[DOC syntax=3]\n[P] text")

    assert any(
        diagnostic.code == DiagnosticCodes.TXT_DUPLICATE_ID
        and diagnostic.severity is Severity.ERROR
        for diagnostic in duplicate_result.diagnostics
    )
    assert invalid_syntax_result.diagnostics[0].code == DiagnosticCodes.TXT_UNSUPPORTED_SYNTAX
    assert invalid_syntax_result.diagnostics[0].severity is Severity.ERROR


def test_v2_parser_parses_extended_table_compliance_attributes():
    result = V2Parser().parse(
        "\n".join(
            [
                '[TABLE id=t1 caption="Параметры" number=3 unit="МПа" continuation=continuation '
                'column_units="-,Гц,°С" header_rows=2]',
                "| Колонка 1 | Колонка 2 | Колонка 3 |",
                "|-----------|-----------|-----------|",
                "| Параметр | Частота | Температура |",
                "| Давление | 50 | 20 |",
                '[TABLE_NOTE marker="*" text="Измерено при нормальных условиях"]',
                "[TABLE_END]",
            ]
        )
    )

    assert result.diagnostics == []
    table = result.document.blocks[0]
    assert isinstance(table, TableNode)
    assert table.id == "t1"
    assert table.caption == "Параметры"
    assert table.number == "3"
    assert table.unit_label == "МПа"
    assert getattr(table.continuation, "value", table.continuation) == "continuation"
    assert table.column_units == (None, "Гц", "°С")
    assert table.header_row_count == 2
    assert tuple(tuple(cell.text for cell in row.cells) for row in table.rows) == (
        ("Колонка 1", "Колонка 2", "Колонка 3"),
        ("Параметр", "Частота", "Температура"),
        ("Давление", "50", "20"),
    )
    assert [(note.marker, note.text) for note in table.notes] == [
        ("*", "Измерено при нормальных условиях"),
    ]


def test_v2_parser_preserves_nested_lists_by_level():
    result = V2Parser().parse(
        "\n".join(
            [
                "[LIST type=lettered level=1]",
                "[а)] основной пункт",
                "[LIST type=numbered level=2]",
                "[1)] вложенный пункт",
                "[LIST_END]",
                "[LIST_END]",
            ]
        )
    )

    assert result.diagnostics == []
    (list_block,) = result.document.blocks
    assert list_block.list_type is ListType.LETTERED
    first_item = list_block.items[0]
    assert first_item.text == "основной пункт"
    assert len(first_item.children) == 1
    nested = first_item.children[0]
    assert nested.list_type is ListType.NUMBERED
    assert [item.text for item in nested.items] == ["вложенный пункт"]


def test_v2_parser_parses_section_setup_with_nested_blocks():
    result = V2Parser().parse(
        "\n".join(
            [
                "[SECTION orientation=landscape sheet=A3 frame=text_following form=form_3]",
                "[P] Section body",
                "[/SECTION]",
            ]
        )
    )

    assert result.diagnostics == []
    (section,) = result.document.blocks
    assert isinstance(section, SectionSetupNode)
    assert section.orientation is SectionOrientation.LANDSCAPE
    assert section.sheet_format is SheetFormat.A3
    assert section.frame is FrameType.TEXT_FOLLOWING
    assert section.title_block_form is TitleBlockForm.FORM_3
    assert isinstance(section.blocks[0], ParagraphNode)
    assert section.blocks[0].runs[0].text == "Section body"
