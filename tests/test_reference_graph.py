from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    Citation,
    CitationNode,
    Document,
    FigureNode,
    ParagraphNode,
    SourceRecordNode,
    SourceRecordType,
    TextRun,
)
from sfu_converter.domain.diagnostics import DiagnosticCodes, Severity
from sfu_converter.domain.reference_graph import ReferenceTargetKind, build_reference_graph
from sfu_converter.parser.v2_parser import V2Parser


def _codes(document: Document) -> list[str]:
    return [diagnostic.code for diagnostic in build_reference_graph(document).diagnostics()]


def test_figure_reference_by_standard_phrase_resolves_cleanly():
    document = V2Parser().parse(
        "\n".join(
            [
                '[FIGURE id=f1 caption="Схема"]',
                "[P] Как показано на (рисунок 1), процесс устойчив.",
            ]
        )
    ).document

    graph = build_reference_graph(document)

    assert graph.references_to(ReferenceTargetKind.FIGURE, "f1")
    assert graph.diagnostics() == []


def test_missing_figure_reference_reports_unresolved_error():
    document = V2Parser().parse("[P] Нет объекта (рисунок 99).").document

    diagnostics = build_reference_graph(document).diagnostics()

    assert diagnostics[0].code == DiagnosticCodes.REFERENCE_UNRESOLVED
    assert diagnostics[0].severity is Severity.ERROR
    assert diagnostics[0].target == "figure:99"


def test_unreferenced_figure_reports_object_unused_warning():
    document = Document(blocks=(FigureNode(src=None, caption="Схема", id="fig:missing"),))

    diagnostics = build_reference_graph(document).diagnostics()

    assert diagnostics[0].code == DiagnosticCodes.REFERENCE_OBJECT_UNUSED
    assert diagnostics[0].severity is Severity.WARNING
    assert diagnostics[0].target == "fig:missing"


def test_duplicate_figure_definition_reports_ambiguous_reference():
    document = Document(
        blocks=(
            FigureNode(src=None, caption="Один", id="dup"),
            FigureNode(src=None, caption="Два", id="dup"),
            ParagraphNode(runs=(TextRun("См. (рисунок 1)."),)),
        )
    )

    diagnostics = build_reference_graph(document).diagnostics()

    assert DiagnosticCodes.REFERENCE_AMBIGUOUS in [diagnostic.code for diagnostic in diagnostics]


def test_appendix_reference_marks_appendix_used():
    document = V2Parser().parse(
        "\n".join(
            [
                '[APPENDIX id=app:a letter="А" title="ПРИЛОЖЕНИЕ А"]',
                "[P] Данные приведены в (см. приложение А).",
            ]
        )
    ).document

    graph = build_reference_graph(document)

    assert graph.references_to(ReferenceTargetKind.APPENDIX, "app:a")
    assert DiagnosticCodes.REFERENCE_APPENDIX_UNUSED not in _codes(document)


def test_source_record_without_citation_reports_bibliography_unused():
    document = Document(
        blocks=(
            SourceRecordNode(
                number=7,
                record_type=SourceRecordType.BOOK_ONE_AUTHOR,
                fields={"authors": "Иванов И.И.", "title": "Книга"},
                language="ru",
            ),
        )
    )

    diagnostics = build_reference_graph(document).diagnostics()

    assert diagnostics[0].code == DiagnosticCodes.REFERENCE_BIBLIOGRAPHY_UNUSED
    assert diagnostics[0].severity is Severity.WARNING
    assert diagnostics[0].target == "source:7"


def test_source_citation_creates_inbound_source_edge():
    document = Document(
        blocks=(
            ParagraphNode(runs=(TextRun("См. "), CitationNode((Citation(7),)))),
            SourceRecordNode(
                number=7,
                record_type=SourceRecordType.BOOK_ONE_AUTHOR,
                fields={"authors": "Иванов И.И.", "title": "Книга"},
                language="ru",
            ),
        )
    )

    graph = build_reference_graph(document)

    assert graph.references_to(ReferenceTargetKind.SOURCE, "source:7")
    assert graph.diagnostics() == []
