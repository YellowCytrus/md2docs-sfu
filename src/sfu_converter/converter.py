from __future__ import annotations

import logging
from pathlib import Path

from sfu_converter.application.convert import ConvertTextToDocx
from sfu_converter.config import PathConfig, SIBFUConfig
from sfu_converter.domain.constants import DEFAULT_PROFILE_NAME
from sfu_converter.domain.ast_nodes import Document as AstDocument
from sfu_converter.domain.diagnostics import Severity
from sfu_converter.domain.formatting import FormattingProfile
from sfu_converter.infrastructure.docx_renderer import DocxRenderer
from sfu_converter.parser import DEFAULT_SYNTAX_VERSION, get_parser
from sfu_converter.registry import get_profile


class TextToDocxConverter:
    """Compatibility wrapper for TXT to DOCX conversion."""

    def __init__(self, config_class=SIBFUConfig, base_dir=None):
        self.config = config_class
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.logger = logging.getLogger(__name__)
        self.diagnostics = []
        self._renderer = DocxRenderer(
            config_class=self.config,
            base_dir=self.base_dir,
            logger=self.logger,
        )

    @property
    def doc(self):
        return self._renderer.doc

    @doc.setter
    def doc(self, value):
        self._renderer.doc = value

    def _set_run_style(self, run, bold=False):
        return self._renderer._set_run_style(run, bold)

    def _set_paragraph_format(self, para, style_type="normal"):
        return self._renderer._set_paragraph_format(para, style_type)

    def _add_empty_paragraph(self, style_type="empty_after_image"):
        return self._renderer._add_empty_paragraph(style_type)

    def _insert_image(self, image_path=None, caption=None):
        return self._renderer._insert_image(image_path, caption)

    def _parse_table_line(self, line):
        return self._renderer._parse_table_line(line)

    def _create_table(self, rows_data, caption=None):
        return self._renderer._create_table(rows_data, caption)

    def _setup_document_margins(self):
        return self._renderer._setup_document_margins()

    def _load_template(self, template_path):
        return self._renderer._load_template(template_path)

    def _initialize_document(self, template=None):
        return self._renderer._initialize_document(template)

    def _render_lines(self, lines):
        """Render source lines or an AST into the current document."""
        if isinstance(lines, AstDocument):
            self._renderer._render_from_ast(lines)
            return

        source = self._lines_to_source(lines)
        result = get_parser().parse(source)
        self._log_parser_diagnostics(result.diagnostics)
        self._renderer._render_from_ast(result.document)

    def _lines_to_source(self, lines):
        if isinstance(lines, str):
            return lines

        source_lines = list(lines)
        if any(line.endswith(("\n", "\r")) for line in source_lines):
            return "".join(source_lines)
        return "\n".join(source_lines)

    def _log_parser_diagnostics(self, diagnostics):
        for diagnostic in diagnostics:
            line = diagnostic.source.line_start if diagnostic.source else "?"
            message = f"{diagnostic.code} at line {line}: {diagnostic.message}"
            if diagnostic.severity in (Severity.ERROR, Severity.FATAL):
                self.logger.error(message)
            else:
                self.logger.warning(message)

    def convert_file(
        self,
        input_file: Path,
        output_file: Path,
        template: str | None = None,
        template_mode: str = "append",
        insert_after_page: int | None = None,
        insert_at_bookmark: str | None = None,
        syntax_version: int = DEFAULT_SYNTAX_VERSION,
        strict: bool = False,
        skip_generated_front_matter: bool = False,
        *,
        profile: FormattingProfile,
    ):
        """Convert a TXT file by explicit input and output paths."""
        input_file = Path(input_file)
        output_file = Path(output_file)

        self.logger.info(f"Начало конвертации: {input_file}")
        source = input_file.read_text(encoding="utf-8")
        use_case = ConvertTextToDocx(
            get_parser(syntax_version, strict=strict),
            self._renderer,
        )

        composing_into_template = template is not None and (
            template_mode in ("preserve-prefix", "replace-body")
            or insert_after_page is not None
            or insert_at_bookmark is not None
        )

        renderer_template = None if composing_into_template else (str(template) if template is not None else None)

        diagnostics = use_case.execute(
            source=source,
            profile=profile,
            output_path=str(output_file),
            template_path=renderer_template,
            template_mode=template_mode,
            filename=str(input_file),
            skip_generated_front_matter=skip_generated_front_matter,
        )
        self.diagnostics = diagnostics
        self._log_parser_diagnostics(diagnostics)

        if composing_into_template:
            from sfu_converter.infrastructure.template_adapter import (
                DocxTemplateAdapter,
            )

            adapter = DocxTemplateAdapter(base_dir=self.base_dir, logger=self.logger)
            tmpl = adapter.load_template(str(template))
            insertion = adapter.find_insertion_point(
                tmpl,
                mode=template_mode,
                page=insert_after_page,
                bookmark=insert_at_bookmark,
            )
            if not insertion.found:
                if insertion.diagnostic is not None:
                    diagnostics.append(insertion.diagnostic)
                self.logger.error("Template composition aborted: insertion point not found")
            else:
                generated_bytes = output_file.read_bytes()
                composed = adapter.compose(tmpl, insertion, generated_bytes)
                output_file.write_bytes(composed)

        self.logger.info(f"Конвертация завершена: {output_file}")
        return str(output_file)

    def convert(self, input_path, output_path=None, template=None):
        """Backward-compatible conversion through examples/ and results/."""
        if output_path is None:
            return None

        input_file = self.base_dir / PathConfig.EXAMPLES_DIR / input_path
        output_file = self.base_dir / PathConfig.RESULTS_DIR / output_path
        return self.convert_file(input_file, output_file, template, profile=get_profile(DEFAULT_PROFILE_NAME))
