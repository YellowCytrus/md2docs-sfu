"""Form В — Дипломный проект (Diploma Project)."""
from __future__ import annotations
from typing import Any
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, resolve_document_type, SIGNATURE_LINE

FORM_ID = "form_v"
DEFAULT_DOCUMENT_TYPE = "ДИПЛОМНЫЙ ПРОЕКТ"
REQUIRED_METADATA: tuple[str, ...] = ("title", "student", "supervisor")
OPTIONAL_METADATA: tuple[str, ...] = (
    "document_type", "specialty_code", "specialty_name",
    "consultants", "norm_controller",
    "institute", "department", "city", "year",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    layout.add_header(metadata)
    layout.add_blank(2)
    layout.add_approval_block(metadata)
    layout.add_blank(2)
    doc_type = resolve_document_type(metadata, DEFAULT_DOCUMENT_TYPE)
    layout.add_centered(doc_type, bold=True)
    layout.add_centered("Пояснительная записка")
    title = metadata.get("title", "")
    if title:
        layout.add_centered(title, bold=True)
    specialty_code = metadata.get("specialty_code", "")
    specialty_name = metadata.get("specialty_name", "")
    if specialty_code or specialty_name:
        layout.add_centered(f"по специальности {specialty_code} {specialty_name}".strip())
    layout.add_blank(2)
    supervisor = metadata.get("supervisor", "")
    if supervisor:
        layout.add_signatory("Руководитель", supervisor, title=metadata.get("supervisor_title"))
    consultants = metadata.get("consultants", "")
    if consultants:
        if isinstance(consultants, str):
            for line in consultants.split(";"):
                line = line.strip()
                if line:
                    layout.add_signatory("Консультант", line)
    norm_controller = metadata.get("norm_controller", "")
    if norm_controller:
        layout.add_signatory("Нормоконтролёр", norm_controller)
    student = metadata.get("student", "")
    if student:
        layout.add_signatory("Дипломник", student)
    layout.add_blank(2)
    layout.add_footer(metadata)
