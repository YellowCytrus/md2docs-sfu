from __future__ import annotations

from sfu_converter.application import composition, heading_checks, metadata_check
from sfu_converter.application.style_check import validate_style
from sfu_converter.application.units import validate_unit_consistency
from sfu_converter.domain.diagnostics import Diagnostic
from sfu_converter.domain.formatting import FormattingProfile, unsupported_rule_diagnostics
from sfu_converter.domain.reference_graph import build_reference_graph
from sfu_converter.infrastructure.appendix import assign_appendix_letters
from sfu_converter.infrastructure.graphics import validate as validate_graphics
from sfu_converter.infrastructure.project_designation import validate_document_designations
from sfu_converter.parser.base import BaseParser
from sfu_converter.ports.renderer import RendererPort


class ConvertTextToDocx:
    def __init__(self, parser: BaseParser, renderer: RendererPort):
        self._parser = parser
        self._renderer = renderer

    def execute(
        self,
        source: str,
        profile: FormattingProfile,
        output_path: str,
        template_path: str | None = None,
        template_mode: str = "append",
        filename: str | None = None,
        skip_generated_front_matter: bool = False,
    ) -> list[Diagnostic]:
        result = self._parser.parse(source, filename)
        document, appendix_diagnostics = assign_appendix_letters(result.document)
        diagnostics = list(result.diagnostics)
        diagnostics.extend(appendix_diagnostics)
        diagnostics.extend(unsupported_rule_diagnostics(profile, component="renderer"))
        diagnostics.extend(composition.validate(document, profile))
        diagnostics.extend(metadata_check.run(document, profile))
        diagnostics.extend(validate_document_designations(document, profile))
        diagnostics.extend(heading_checks.run(document, profile))
        diagnostics.extend(validate_graphics(document, profile))
        diagnostics.extend(validate_style(document))
        diagnostics.extend(validate_unit_consistency(document))
        diagnostics.extend(build_reference_graph(document).diagnostics())
        render_diagnostics = self._renderer.render_to_file(
            document,
            profile,
            output_path,
            template_path,
            template_mode,
            skip_generated_front_matter=skip_generated_front_matter,
        )
        diagnostics.extend(_without_existing_support_diagnostics(diagnostics, render_diagnostics))
        return diagnostics


def _without_existing_support_diagnostics(
    existing: list[Diagnostic],
    candidates: list[Diagnostic],
) -> list[Diagnostic]:
    seen = {
        (diagnostic.code, diagnostic.rule_id, diagnostic.message)
        for diagnostic in existing
    }
    return [
        diagnostic
        for diagnostic in candidates
        if (diagnostic.code, diagnostic.rule_id, diagnostic.message) not in seen
    ]
