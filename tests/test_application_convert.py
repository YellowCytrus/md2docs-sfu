from sfu_converter.application.convert import ConvertTextToDocx
from sfu_converter.domain.ast_nodes import (
    Document,
    HeadingLevel,
    HeadingNode,
    ParagraphNode,
    TextRun,
    TitlePageNode,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile, FormattingRule, RuleSeverity, RuleStatus
from sfu_converter.parser.base import ParserResult
from sfu_converter.registry import get_profile


class FakeParser:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def parse(self, source, filename=None):
        self.calls.append((source, filename))
        return self.result


class FakeRenderer:
    def __init__(self, diagnostics=None):
        self.diagnostics = diagnostics or []
        self.calls = []

    def render(self, document, profile, template_path=None, template_mode="append"):
        return b"unused"

    def render_to_file(
        self,
        document,
        profile,
        output_path,
        template_path=None,
        template_mode="append",
        skip_generated_front_matter=False,
    ):
        self.calls.append(
            (
                document,
                profile,
                output_path,
                template_path,
                template_mode,
                skip_generated_front_matter,
            )
        )
        return self.diagnostics


def test_convert_text_to_docx_parses_source_and_renders_document():
    document = Document(blocks=(ParagraphNode(runs=(TextRun("Body"),)),))
    parse_diagnostic = Diagnostic("TXT_WARNING", "warning", Severity.WARNING)
    render_diagnostic = Diagnostic("RENDER_WARNING", "warning", Severity.WARNING)
    parser = FakeParser(ParserResult(document, [parse_diagnostic]))
    renderer = FakeRenderer([render_diagnostic])
    profile = FormattingProfile(
        name="common",
        display_name="Common",
        source_docs=("standard",),
    )
    use_case = ConvertTextToDocx(parser, renderer)

    diagnostics = use_case.execute(
        "source text",
        profile,
        "out.docx",
        template_path="template.docx",
        filename="input.txt",
    )

    assert parser.calls == [("source text", "input.txt")]
    assert renderer.calls == [(document, profile, "out.docx", "template.docx", "append", False)]
    assert diagnostics == [parse_diagnostic, render_diagnostic]


def test_convert_text_to_docx_preserves_profile_object_for_renderer():
    document = Document(blocks=(ParagraphNode(runs=(TextRun("Body"),)),))
    parser = FakeParser(ParserResult(document, []))
    renderer = FakeRenderer()
    profile = FormattingProfile(
        name="research_reports",
        display_name="Research Reports",
        source_docs=("standard",),
    )

    ConvertTextToDocx(parser, renderer).execute("source text", profile, "out.docx")

    assert renderer.calls[0][1] is profile


def test_convert_text_to_docx_passes_front_matter_skip_to_renderer():
    document = Document(blocks=(ParagraphNode(runs=(TextRun("Body"),)),))
    parser = FakeParser(ParserResult(document, []))
    renderer = FakeRenderer()
    profile = FormattingProfile(
        name="common",
        display_name="Common",
        source_docs=("standard",),
    )

    ConvertTextToDocx(parser, renderer).execute(
        "source text",
        profile,
        "out.docx",
        skip_generated_front_matter=True,
    )

    assert renderer.calls[0][5] is True


def test_convert_text_to_docx_reports_unsupported_renderer_rules():
    document = Document(blocks=(ParagraphNode(runs=(TextRun("Body"),)),))
    parser = FakeParser(ParserResult(document, []))
    renderer = FakeRenderer()
    unsupported_rule = FormattingRule(
        id="synthetic.renderer.rule",
        source_doc="docs/formatting requirements/common.md",
        source_section="Synthetic",
        severity=RuleSeverity.REQUIRED,
        renderer_status=RuleStatus.NOT_SUPPORTED,
        validator_status=RuleStatus.IMPLEMENTED,
    )
    profile = FormattingProfile(
        name="synthetic",
        display_name="Synthetic",
        source_docs=("standard",),
        rules=(unsupported_rule,),
    )

    diagnostics = ConvertTextToDocx(parser, renderer).execute("source text", profile, "out.docx")

    assert diagnostics[0].code == DiagnosticCodes.FORMAT_RULE_NOT_SUPPORTED
    assert diagnostics[0].severity is Severity.WARNING
    assert diagnostics[0].rule_id == "synthetic.renderer.rule"


def test_convert_text_to_docx_reports_composition_diagnostics():
    document = Document(blocks=(ParagraphNode(runs=(TextRun("Body"),)),))
    parser = FakeParser(ParserResult(document, []))
    renderer = FakeRenderer()
    profile = get_profile("coursework")

    diagnostics = ConvertTextToDocx(parser, renderer).execute("source text", profile, "out.docx")

    codes = [d.code for d in diagnostics]
    assert DiagnosticCodes.STRUCTURE_TITLE_PAGE_MISSING in codes
    assert DiagnosticCodes.STRUCTURE_MAIN_PART_MISSING in codes


def test_convert_text_to_docx_reports_reference_graph_diagnostics():
    document = Document(blocks=(ParagraphNode(runs=(TextRun("Нет объекта (рисунок 99)."),)),))
    parser = FakeParser(ParserResult(document, []))
    renderer = FakeRenderer()
    profile = get_profile("common")

    diagnostics = ConvertTextToDocx(parser, renderer).execute("source text", profile, "out.docx")

    assert any(
        diagnostic.code == DiagnosticCodes.REFERENCE_UNRESOLVED
        and diagnostic.target == "figure:99"
        for diagnostic in diagnostics
    )


def test_convert_text_to_docx_omits_composition_diagnostics_when_valid():
    document = Document(
        blocks=(
            TitlePageNode(),
            HeadingNode(level=HeadingLevel.H1, text="Раздел 1"),
            ParagraphNode(runs=(TextRun("Body"),)),
        )
    )
    parser = FakeParser(ParserResult(document, []))
    renderer = FakeRenderer()
    profile = get_profile("lab_practical_project_reports")

    diagnostics = ConvertTextToDocx(parser, renderer).execute("source text", profile, "out.docx")

    structure_codes = [d.code for d in diagnostics if d.code.startswith("STRUCTURE_")]
    assert structure_codes == []
