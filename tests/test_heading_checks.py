from sfu_converter.application.heading_checks import run
from sfu_converter.domain.ast_nodes import Document, HeadingLevel, HeadingNode, SourceSpan
from sfu_converter.domain.diagnostics import DiagnosticCodes
from sfu_converter.registry import get_profile


def _heading(level: HeadingLevel, text: str, line: int) -> HeadingNode:
    return HeadingNode(
        level=level,
        text=text,
        number="auto",
        source=SourceSpan(line, line),
    )


def _run(*blocks):
    return run(Document(blocks=blocks), get_profile("common"))


def test_two_sentence_heading_accepts_separator_without_final_period():
    diagnostics = _run(_heading(HeadingLevel.H2, "Первая часть. Вторая часть", 1))

    assert not any(
        diagnostic.code == DiagnosticCodes.HEADING_TWO_SENTENCE
        for diagnostic in diagnostics
    )


def test_two_sentence_heading_rejects_second_sentence_final_period():
    diagnostics = _run(_heading(HeadingLevel.H2, "Первая часть. Вторая часть.", 1))

    assert any(
        diagnostic.code == DiagnosticCodes.HEADING_TWO_SENTENCE
        and diagnostic.rule_id == "common.heading.two_sentence_separator"
        for diagnostic in diagnostics
    )


def test_heading_hyphenation_rejects_soft_hyphen_and_explicit_line_break():
    diagnostics = _run(
        _heading(HeadingLevel.H2, "Много\u00adступенчатый анализ", 1),
        _heading(HeadingLevel.H2, "Много-\nстрочный заголовок", 2),
    )

    assert [
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.code == DiagnosticCodes.HEADING_HYPHENATION
    ] == [
        DiagnosticCodes.HEADING_HYPHENATION,
        DiagnosticCodes.HEADING_HYPHENATION,
    ]


def test_single_point_section_with_one_subpoint_is_accepted():
    diagnostics = _run(
        _heading(HeadingLevel.H1, "Раздел", 1),
        _heading(HeadingLevel.H2, "Подраздел", 2),
        _heading(HeadingLevel.H3, "Пункт", 3),
        _heading(HeadingLevel.H4, "Подпункт", 4),
    )

    assert not any(
        diagnostic.code == DiagnosticCodes.HEADING_POINT_REQUIRES_SUBPOINTS
        for diagnostic in diagnostics
    )


def test_point_with_single_subpoint_in_multi_point_section_is_reported():
    diagnostics = _run(
        _heading(HeadingLevel.H1, "Раздел", 1),
        _heading(HeadingLevel.H2, "Подраздел", 2),
        _heading(HeadingLevel.H3, "Пункт один", 3),
        _heading(HeadingLevel.H4, "Единственный подпункт", 4),
        _heading(HeadingLevel.H3, "Пункт два", 5),
    )

    assert any(
        diagnostic.code == DiagnosticCodes.HEADING_POINT_REQUIRES_SUBPOINTS
        and diagnostic.rule_id == "common.heading.point_requires_subpoints"
        and diagnostic.source == SourceSpan(3, 3)
        for diagnostic in diagnostics
    )
