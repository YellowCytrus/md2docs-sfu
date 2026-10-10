from sfu_converter.application import composition
from sfu_converter.domain.ast_nodes import (
    Document,
    HeadingLevel,
    HeadingNode,
    ParagraphNode,
    SourceSpan,
    StructuralSectionNode,
    StructuralSectionType,
    TextRun,
    TitlePageNode,
)
from sfu_converter.domain.diagnostics import DiagnosticCodes, Severity
from sfu_converter.infrastructure.docx_validator import diagnostic_to_json
from sfu_converter.registry import get_profile


def _section(section_type, line):
    return StructuralSectionNode(
        section_type=section_type,
        title=section_type.value,
        source=SourceSpan(line, line),
    )


def _heading(text, line):
    return HeadingNode(level=HeadingLevel.H1, text=text, source=SourceSpan(line, line))


def _codes(diagnostics):
    return [d.code for d in diagnostics]


def test_missing_title_page_reports_coursework_rule_id():
    document = Document(
        blocks=(
            _heading("Раздел 1", 1),
            ParagraphNode(runs=(TextRun("Body"),)),
        )
    )

    diagnostics = composition.validate(document, get_profile("coursework"))

    title_diag = next(
        d for d in diagnostics if d.code == DiagnosticCodes.STRUCTURE_TITLE_PAGE_MISSING
    )
    assert title_diag.rule_id == "coursework.title_page.form_i"
    assert title_diag.severity is Severity.WARNING


def test_appendix_before_sources_reports_diagnostic():
    document = Document(
        blocks=(
            TitlePageNode(),
            _heading("Раздел 1", 2),
            _section(StructuralSectionType.APPENDIX, 3),
            _section(StructuralSectionType.SOURCES, 4),
        )
    )

    diagnostics = composition.validate(document, get_profile("coursework"))

    assert DiagnosticCodes.STRUCTURE_APPENDIX_BEFORE_SOURCES in _codes(diagnostics)


def test_duplicate_contents_reports_single_diagnostic_with_both_spans():
    document = Document(
        blocks=(
            TitlePageNode(),
            _section(StructuralSectionType.CONTENTS, 2),
            _section(StructuralSectionType.CONTENTS, 7),
            _heading("Раздел 1", 9),
        )
    )

    diagnostics = composition.validate(document, get_profile("coursework"))

    duplicates = [
        d for d in diagnostics if d.code == DiagnosticCodes.STRUCTURE_DUPLICATE_SECTION
    ]
    assert len(duplicates) == 1
    lines = {duplicates[0].source.line_start, duplicates[0].data["duplicate_line"]}
    assert lines == {2, 7}


def test_minimal_valid_lab_report_passes():
    document = Document(
        blocks=(
            TitlePageNode(),
            _heading("Раздел 1", 2),
            ParagraphNode(runs=(TextRun("Body"),)),
        )
    )

    diagnostics = composition.validate(
        document, get_profile("lab_practical_project_reports")
    )

    assert diagnostics == []


def test_research_report_missing_introduction_reports_required_section():
    document = Document(
        blocks=(
            TitlePageNode(),
            _heading("Раздел 1", 2),
            ParagraphNode(runs=(TextRun("Body"),)),
        )
    )

    diagnostics = composition.validate(document, get_profile("research_reports"))

    missing = [
        d
        for d in diagnostics
        if d.code == DiagnosticCodes.STRUCTURE_REQUIRED_SECTION_MISSING
    ]
    assert any(d.data["section"] == StructuralSectionType.INTRODUCTION.name for d in missing)


def test_sources_before_abbreviations_reports_diagnostic():
    document = Document(
        blocks=(
            TitlePageNode(),
            _heading("Раздел 1", 2),
            _section(StructuralSectionType.SOURCES, 3),
            _section(StructuralSectionType.ABBREVIATIONS, 4),
        )
    )

    diagnostics = composition.validate(document, get_profile("coursework"))

    assert DiagnosticCodes.STRUCTURE_SOURCES_BEFORE_ABBREVIATIONS in _codes(diagnostics)


def test_introduction_after_conclusion_reports_out_of_order():
    document = Document(
        blocks=(
            TitlePageNode(),
            _section(StructuralSectionType.CONCLUSION, 2),
            _section(StructuralSectionType.INTRODUCTION, 3),
        )
    )

    diagnostics = composition.validate(document, get_profile("coursework"))

    out_of_order = [
        d for d in diagnostics if d.code == DiagnosticCodes.STRUCTURE_SECTION_OUT_OF_ORDER
    ]
    assert len(out_of_order) == 1
    diag = out_of_order[0]
    assert diag.data["section"] == StructuralSectionType.INTRODUCTION.name
    assert diag.data["expected_after"] == StructuralSectionType.CONTENTS.name
    assert diag.source.line_start == 3


def test_composition_diagnostics_serialize_with_spans_intact():
    document = Document(
        blocks=(
            TitlePageNode(),
            _section(StructuralSectionType.CONTENTS, 2),
            _section(StructuralSectionType.CONTENTS, 7),
            _heading("Раздел 1", 9),
        )
    )

    diagnostics = composition.validate(document, get_profile("coursework"))
    duplicate = next(
        d for d in diagnostics if d.code == DiagnosticCodes.STRUCTURE_DUPLICATE_SECTION
    )

    payload = diagnostic_to_json(duplicate)

    assert payload["code"] == DiagnosticCodes.STRUCTURE_DUPLICATE_SECTION
    assert payload["data"]["duplicate_line"] == 7
    assert duplicate.source.line_start == 2
