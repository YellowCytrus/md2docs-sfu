from __future__ import annotations

import logging
from pathlib import Path

from sfu_converter.config import SIBFUConfig
from sfu_converter.domain.constants import DEFAULT_PROFILE_NAME
from sfu_converter.domain.diagnostics import Severity
from sfu_converter.domain.formatting import FormattingProfile
from sfu_converter.infrastructure.docx_validator import (
    DocxValidator,
    diagnostic_to_json,
)
from sfu_converter.registry import get_profile


class StyleValidator:
    """Backward-compatible facade over the registry-backed DOCX validator."""

    def __init__(
        self,
        config_class=SIBFUConfig,
        profile: FormattingProfile | str | None = None,
        *,
        profile_name: str | None = None,
    ):
        self.config = config_class
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.diagnostics = []
        self.logger = logging.getLogger(__name__)
        selected_profile = _resolve_profile(profile, profile_name)
        self._validator = DocxValidator(selected_profile, config_class=config_class)

    def _get_pt_value(self, value):
        """Конвертирует значение в пункты (pt)."""
        if value is None:
            return 0
        if hasattr(value, "pt"):
            return value.pt
        return float(value) if value else 0

    def _is_header_paragraph(self, para):
        """Определяет заголовок по стилю или по жирному центрированному тексту."""
        return self._validator._is_heading_paragraph(para)

    def validate_font(self, run, para_index):
        """Проверяет шрифт и размер текста."""
        issues = []
        if run.font.name and run.font.name != self.config.FONT_NAME:
            issues.append(f"Абзац {para_index}: Шрифт '{run.font.name}' вместо '{self.config.FONT_NAME}'")

        current_size = self._get_pt_value(run.font.size)
        if current_size > 0 and abs(current_size - self.config.FONT_SIZE.pt) > 0.5:
            issues.append(f"Абзац {para_index}: Размер {current_size}pt вместо {self.config.FONT_SIZE.pt}pt")

        return issues

    def validate_paragraph_spacing(self, para, para_index):
        """Проверяет интервалы между абзацами (должны быть 0)."""
        issues = []
        pf = para.paragraph_format

        if pf.space_before and pf.space_before.pt > 1:
            issues.append(f"Абзац {para_index}: Интервал перед {pf.space_before.pt:.1f}pt (должен быть 0)")

        if pf.space_after and pf.space_after.pt > 1:
            issues.append(f"Абзац {para_index}: Интервал после {pf.space_after.pt:.1f}pt (должен быть 0)")

        return issues

    def validate_first_line_indent(self, para, para_index):
        """Проверяет отступ первой строки."""
        issues = []
        pf = para.paragraph_format
        current_indent = self._get_pt_value(pf.first_line_indent)

        if self._is_header_paragraph(para):
            if current_indent > 5:
                issues.append(f"Абзац {para_index}: Заголовок имеет отступ {current_indent:.1f}pt (должен быть 0)")
            return issues

        expected_indent_pt = self.config.FIRST_LINE_INDENT.pt
        if abs(current_indent - expected_indent_pt) > 5:
            issues.append(f"Абзац {para_index}: Отступ {current_indent:.1f}pt вместо {expected_indent_pt:.1f}pt")

        return issues

    def validate_line_spacing(self, para, para_index, expected_spacing=1.5):
        """Проверяет межстрочный интервал."""
        issues = []
        pf = para.paragraph_format

        if pf.line_spacing:
            spacing = self._get_pt_value(pf.line_spacing)
            if spacing < 10 and abs(spacing - expected_spacing) > 0.1:
                issues.append(f"Абзац {para_index}: Интервал {spacing} вместо {expected_spacing}")

        return issues

    def validate_file(self, file_path):
        """Выполняет полную валидацию документа."""
        self.logger.info("Начало валидации: %s", file_path)
        self.errors = []
        self.warnings = []
        self.diagnostics = []

        diagnostics = self._validator.validate_file(str(Path(file_path)))
        self.diagnostics = diagnostics
        self.errors = [
            diagnostic.message for diagnostic in diagnostics if diagnostic.severity in (Severity.ERROR, Severity.FATAL)
        ]
        self.warnings = [diagnostic.message for diagnostic in diagnostics if diagnostic.severity is Severity.WARNING]

        if self.errors:
            self.logger.warning("Найдено ошибок: %s", len(self.errors))
            for error in self.errors[:10]:
                self.logger.warning(error)
            return False

        self.logger.info("Валидация пройдена успешно")
        return True

    def get_report(self):
        """Возвращает отчет о валидации."""
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "error_list": self.errors,
            "warning_list": self.warnings,
            "diagnostics": [diagnostic_to_json(diagnostic) for diagnostic in self.diagnostics],
        }


def _resolve_profile(
    profile: FormattingProfile | str | None,
    profile_name: str | None,
) -> FormattingProfile:
    selected = profile if profile is not None else profile_name
    if isinstance(selected, FormattingProfile):
        return selected
    return get_profile(selected or DEFAULT_PROFILE_NAME)
