from dataclasses import FrozenInstanceError, is_dataclass
from types import MappingProxyType
from typing import get_args

import pytest

from sfu_converter.domain.ast_nodes import (
    AbbreviationEntryNode,
    AbbreviationsListNode,
    AppendixNode,
    BibliographyEntryNode,
    BlockNode,
    DrawingSheetNode,
    FigureNode,
    FootnoteAnchor,
    FootnoteNode,
    FormulaNode,
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
    SectionSetupNode,
    SlideDeckNode,
    SlideNode,
    SourceRecordNode,
    SourceRecordType,
    SourceSpan,
    StructuralSectionNode,
    StructuralSectionType,
    TableCaptionNode,
    TableCell,
    TableNode,
    TableNote,
    TableOfContentsNode,
    TableRow,
    TextRun,
    TitlePageNode,
    Document,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import (
    FormattingProfile,
    FormattingRule,
    RuleSeverity,
    RuleStatus,
)
from sfu_converter.domain.values import Length, Margins, Spacing


def _assert_frozen(instance):
    assert is_dataclass(instance)
    with pytest.raises(FrozenInstanceError):
        instance.source = None


def test_ast_nodes_are_frozen_dataclasses():
    span = SourceSpan(line_start=1, line_end=1, col_start=2, col_end=8)
    text_run = TextRun(text="Text", source=span)
    paragraph = ParagraphNode(runs=(text_run,), source=span)
    heading = HeadingNode(level=HeadingLevel.H1, text="Heading", source=span)
    table = TableNode(
        rows=(TableRow(cells=(TableCell("A"), TableCell("B"))),),
        caption="Table 1",
        notes=(TableNote(marker="*", text="Note", source=span),),
        source=span,
    )
    abbreviation = AbbreviationEntryNode(short="ИАК", long="информационно-аналитический комплекс", source=span)
    abbreviations = AbbreviationsListNode(entries=(abbreviation,), source=span)
    table_caption = TableCaptionNode(text="Table 1", source=span)
    figure = FigureNode(src="chart.png", caption="Figure 1", source=span)
    formula = FormulaNode(content="E = mc^2", source=span)
    list_item = ListItemNode(text="Item", source=span)
    list_node = ListNode(list_type=ListType.BULLET, items=(list_item,), source=span)
    appendix = AppendixNode(title="Appendix A", blocks=(paragraph,), source=span)
    bibliography = BibliographyEntryNode(number=1, text="Source", source=span)
    source_record = SourceRecordNode(
        number=2,
        record_type=SourceRecordType.BOOK_ONE_AUTHOR,
        fields={"authors": "Author A.", "title": "Book"},
        language="en",
        source=span,
    )
    footnote_anchor = FootnoteAnchor(marker="1", source=span)
    footnote = FootnoteNode(marker="1", text="Footnote", source=span)
    reference = ReferenceNode(target="fig:overview", source=span)
    raw = RawBlockNode(text="[literal]", source=span)
    metadata = MetadataNode(key="title", value="Report", source=span)
    structural = StructuralSectionNode(
        section_type=StructuralSectionType.INTRODUCTION,
        title="ВВЕДЕНИЕ",
        source=span,
    )

    for instance in (
        span,
        text_run,
        paragraph,
        heading,
        table,
        table_caption,
        figure,
        formula,
        list_item,
        list_node,
        PageBreakNode(source=span),
        appendix,
        bibliography,
        source_record,
        footnote_anchor,
        footnote,
        reference,
        raw,
        metadata,
        structural,
        abbreviation,
        abbreviations,
    ):
        _assert_frozen(instance)


def test_document_accepts_supported_block_types_and_freezes_metadata():
    blocks = (
        HeadingNode(level=HeadingLevel.H1, text="Intro"),
        ParagraphNode(runs=(TextRun("Body"),)),
        TableNode(rows=(TableRow(cells=(TableCell("A"),)),)),
        TableCaptionNode(text="Table 1"),
        FigureNode(src="image.png"),
        FormulaNode(content="x + y"),
        ListNode(list_type=ListType.NUMBERED, items=(ListItemNode("One"),)),
        PageBreakNode(),
        AppendixNode(title="Appendix", blocks=(RawBlockNode("raw"),)),
        BibliographyEntryNode(number=1, text="Book"),
        SourceRecordNode(
            number=2,
            record_type=SourceRecordType.BOOK_ONE_AUTHOR,
            fields={"authors": "Author A.", "title": "Book"},
            language="en",
        ),
        FootnoteNode(marker="1", text="Footnote"),
        ReferenceNode(target="fig:overview"),
        MetadataNode(key="author", value="Student"),
        StructuralSectionNode(
            section_type=StructuralSectionType.CONCLUSION,
            title="ЗАКЛЮЧЕНИЕ",
        ),
        AbbreviationsListNode(
            entries=(AbbreviationEntryNode("ИАК", "информационно-аналитический комплекс"),),
        ),
    )

    document = Document(blocks=blocks, metadata={"title": "Report"}, source_file="input.txt")

    assert document.blocks == blocks
    assert document.syntax_version == 1
    assert document.source_file == "input.txt"
    assert isinstance(document.metadata, MappingProxyType)
    assert document.metadata["title"] == "Report"
    with pytest.raises(TypeError):
        document.metadata["title"] = "Changed"


def test_blocknode_union_contains_all_supported_block_classes():
    assert set(get_args(BlockNode)) == {
        ParagraphNode,
        HeadingNode,
        TableNode,
        TableCaptionNode,
        FigureNode,
        FormulaNode,
        ListNode,
        PageBreakNode,
        AppendixNode,
        BibliographyEntryNode,
        SourceRecordNode,
        FootnoteNode,
        ReferenceNode,
        RawBlockNode,
        MetadataNode,
        StructuralSectionNode,
        TableOfContentsNode,
        TitlePageNode,
        AbbreviationsListNode,
        SectionSetupNode,
        ProjectDesignationNode,
        DrawingSheetNode,
        PosterNode,
        SlideDeckNode,
        SlideNode,
    }


def test_structural_section_types_use_standard_titles():
    assert StructuralSectionType.ABSTRACT.value == "РЕФЕРАТ"
    assert StructuralSectionType.INTRODUCTION.value == "ВВЕДЕНИЕ"
    assert StructuralSectionType.SOURCES.value == "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"


def test_diagnostic_creation_with_all_severity_levels_and_source_span():
    span = SourceSpan(line_start=3, line_end=4, col_start=1, col_end=12, filename="report.txt")

    diagnostics = [
        Diagnostic(
            code=DiagnosticCodes.TXT_UNKNOWN_MARKER,
            message=f"{severity.value} message",
            severity=severity,
            source=span,
            rule_id="common.page.margins.portrait",
            suggestion="Use a known marker",
        )
        for severity in Severity
    ]

    assert [diagnostic.severity for diagnostic in diagnostics] == list(Severity)
    assert diagnostics[0].source == span
    assert diagnostics[0].source.filename == "report.txt"
    assert diagnostics[0].rule_id == "common.page.margins.portrait"


def test_formatting_rule_profile_and_value_objects_are_immutable():
    rule = FormattingRule(
        id="common.page.margins.portrait",
        source_doc="docs/formatting requirements/common.md",
        source_section="Page and paper setup",
        severity=RuleSeverity.REQUIRED,
        parameters={"left": 3, "right": 1},
        renderer_status=RuleStatus.IMPLEMENTED,
        validator_status=RuleStatus.PARTIAL,
        description="Portrait margins",
    )
    profile = FormattingProfile(
        name="lab_practical_project_reports",
        display_name="Lab reports",
        source_docs=("docs/formatting requirements/common.md",),
        rules=(rule,),
    )

    assert isinstance(rule.parameters, MappingProxyType)
    assert profile.rules == (rule,)
    with pytest.raises(FrozenInstanceError):
        rule.description = "Changed"
    with pytest.raises(TypeError):
        rule.parameters["left"] = 2

    spacing = Spacing(before_pt=0, after_pt=6, line=1.5)
    margins = Margins(top_cm=2, bottom_cm=2, left_cm=3, right_cm=1)
    length = Length(value=1.25, unit="cm")

    assert spacing.line == 1.5
    assert margins.left_cm == 3
    assert length.unit == "cm"
    with pytest.raises(FrozenInstanceError):
        spacing.line = 1.0


def test_mapping_proxy_inputs_are_preserved():
    metadata = MappingProxyType({"title": "Report"})
    document = Document(blocks=(), metadata=metadata)
    assert document.metadata is metadata

    parameters = MappingProxyType({"left": 3})
    rule = FormattingRule(
        id="rule",
        source_doc="doc",
        source_section="section",
        severity=RuleSeverity.REQUIRED,
        parameters=parameters,
    )
    assert rule.parameters is parameters
