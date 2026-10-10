"""Generic title page used as the fallback for the ``common`` profile."""
from __future__ import annotations
from typing import Any
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, SIGNATURE_LINE

FORM_ID = "generic"
DEFAULT_DOCUMENT_TYPE = ""
REQUIRED_METADATA: tuple[str, ...] = ()
OPTIONAL_METADATA: tuple[str, ...] = (
    "ministry", "university", "institute", "department",
    "title", "subject", "student", "group",
    "supervisor", "supervisor_title", "city", "year",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    layout.add_header(metadata)
    layout.add_blank(4)
    subject = metadata.get("subject", "")
    if subject:
        layout.add_centered(subject.upper())
    title = metadata.get("title", "")
    if title:
        layout.add_centered(title, bold=True, size=Pt(16))
    layout.add_blank(4)
    supervisor = metadata.get("supervisor", "")
    supervisor_title = metadata.get("supervisor_title", "")
    if supervisor:
        layout.add_signatory("Руководитель", supervisor, title=supervisor_title)
    student = metadata.get("student", "")
    group = metadata.get("group", "")
    if student:
        label = "Студент"
        if group:
            label = f"{label} {group}"
        layout.add_signatory(label, student)
    layout.add_blank(4)
    layout.add_footer(metadata)
