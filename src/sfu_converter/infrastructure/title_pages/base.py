"""Shared helpers and dispatcher for profile-specific title page forms.

Each appendix form (Б, В, Г, Д, Е, Ж, И, К, Л, М, Н) is implemented as a
module under :mod:`sfu_converter.infrastructure.title_pages` exposing
``FORM_ID``, ``DEFAULT_DOCUMENT_TYPE``, ``REQUIRED_METADATA``,
``OPTIONAL_METADATA``, and a ``render(layout, metadata)`` callable. The
:class:`TitlePageLayout` object below wraps a ``python-docx`` document with
the typographic primitives those forms need (centered banner, right-aligned
signatory block, blank-line spacers).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from sfu_converter.domain.constants import DEFAULT_APPROVAL_DATE, DEFAULT_CITY, DEFAULT_YEAR, SIGNATURE_LINE
from sfu_converter.infrastructure.docx_measurements import NO_INDENT_CM


@dataclass
class TitlePageForm:
    """Concrete title page form selected by the dispatcher."""

    form_id: str
    default_document_type: str
    required_metadata: tuple[str, ...]
    optional_metadata: tuple[str, ...]
    render: Callable[["TitlePageLayout", dict[str, Any]], None]


class TitlePageLayout:
    """Typographic primitives shared by all appendix title-page forms."""

    def __init__(self, doc, config):
        self.doc = doc
        self.config = config

    def add_centered(self, text: str, *, bold: bool = False, size: Pt | None = None) -> None:
        self._paragraph(
            text,
            align=WD_ALIGN_PARAGRAPH.CENTER,
            bold=bold,
            size=size,
        )

    def add_right(self, text: str, *, bold: bool = False) -> None:
        self._paragraph(text, align=WD_ALIGN_PARAGRAPH.RIGHT, bold=bold)

    def add_left(self, text: str, *, bold: bool = False) -> None:
        self._paragraph(text, align=WD_ALIGN_PARAGRAPH.LEFT, bold=bold)

    def add_blank(self, count: int = 1) -> None:
        for _ in range(count):
            self._paragraph("", align=WD_ALIGN_PARAGRAPH.CENTER)

    def add_header(self, metadata: dict[str, Any]) -> None:
        ministry = metadata.get(
            "ministry",
            "МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ",
        )
        university = metadata.get("university", "Сибирский федеральный университет")
        self.add_centered(ministry.upper())
        self.add_centered(university.upper(), bold=True)
        institute = metadata.get("institute", "")
        if institute:
            self.add_centered(institute)
        department = metadata.get("department", "")
        if department:
            self.add_centered(department)

    def add_footer(self, metadata: dict[str, Any]) -> None:
        city = metadata.get("city", DEFAULT_CITY)
        year = metadata.get("year", DEFAULT_YEAR)
        footer = " ".join(part for part in (city, year) if part)
        if footer:
            self.add_centered(footer)

    def add_signatory(
        self,
        role: str,
        name: str,
        *,
        title: str | None = None,
        align=WD_ALIGN_PARAGRAPH.RIGHT,
    ) -> None:
        label = role
        if title:
            label = f"{label}, {title}"
        text = f"{label} {SIGNATURE_LINE} {name}".strip()
        self._paragraph(text, align=align)

    def add_approval_block(self, metadata: dict[str, Any]) -> None:
        head = metadata.get("department_head", "")
        approval_date = metadata.get("approval_date", DEFAULT_APPROVAL_DATE)
        self.add_right("УТВЕРЖДАЮ")
        self.add_right(f"Заведующий кафедрой {SIGNATURE_LINE} {head}".strip())
        self.add_right(approval_date)

    def _paragraph(self, text: str, *, align, bold: bool = False, size: Pt | None = None) -> None:
        para = self.doc.add_paragraph()
        para.paragraph_format.alignment = align
        para.paragraph_format.first_line_indent = NO_INDENT_CM
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = 1.0
        run = para.add_run(text)
        run.font.name = self.config.FONT_NAME
        run.font.size = size or self.config.FONT_SIZE
        run.font.color.rgb = RGBColor(*self.config.FONT_COLOR_RGB)
        run.bold = bold
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), self.config.FONT_NAME)


def resolve_document_type(metadata: dict[str, Any], default: str) -> str:
    document_type = metadata.get("document_type")
    if document_type:
        return str(document_type)
    return default
