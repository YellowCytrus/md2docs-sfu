from sfu_converter.application.style_check import (
    find_abbreviations,
    validate_style,
)
from sfu_converter.domain.ast_nodes import (
    Document,
    HeadingLevel,
    HeadingNode,
    ParagraphNode,
    TextRun,
)
from sfu_converter.domain.diagnostics import DiagnosticCodes


def _paragraph(text: str) -> ParagraphNode:
    return ParagraphNode(runs=(TextRun(text),))


def test_find_abbreviations_returns_introduction_sites():
    blocks = (
        _paragraph(
            "информационно-аналитический комплекс (ИАК) используется в системе."
        ),
    )

    assert find_abbreviations(blocks) == [
        ("ИАК", "информационно-аналитический комплекс", None)
    ]


def test_style_check_reports_first_unintroduced_abbreviation_once():
    document = Document(
        blocks=(
            _paragraph("ИАК используется в системе."),
            _paragraph(
                "информационно-аналитический комплекс (ИАК) описан далее."
            ),
            _paragraph("ИАК повторно используется без нового предупреждения."),
        )
    )

    diagnostics = validate_style(document)

    missing = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code == DiagnosticCodes.STYLE_ABBREVIATION_NOT_INTRODUCED
    ]
    assert len(missing) == 1
    assert missing[0].data["abbreviation"] == "ИАК"


def test_style_check_reports_each_abbreviation_in_heading():
    document = Document(
        blocks=(
            HeadingNode(
                level=HeadingLevel.H1,
                text="Описание ИАК и ЦОД",
            ),
        )
    )

    diagnostics = validate_style(document)

    heading = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code == DiagnosticCodes.STYLE_ABBREVIATION_IN_HEADING
    ]
    assert {diagnostic.data["abbreviation"] for diagnostic in heading} == {"ИАК", "ЦОД"}
    assert all(
        diagnostic.rule_id == "common.style.no_abbreviations_in_headings"
        for diagnostic in heading
    )
