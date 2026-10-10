"""Form Ж — Combined single-page VKR title page."""
from __future__ import annotations
from typing import Any
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, resolve_document_type

FORM_ID = "form_zh"
DEFAULT_DOCUMENT_TYPE = "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА"
REQUIRED_METADATA: tuple[str, ...] = ("title", "student", "supervisor")
OPTIONAL_METADATA: tuple[str, ...] = (
    "document_type", "reviewer", "consultants", "norm_controller",
    "direction_code", "direction_name",
    "department_head", "approval_date",
    "institute", "department", "city", "year",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    layout.add_header(metadata)
    layout.add_blank(2)
    layout.add_approval_block(metadata)
    layout.add_blank(2)
    doc_type = resolve_document_type(metadata, DEFAULT_DOCUMENT_TYPE)
    layout.add_centered(doc_type, bold=True)
    title = metadata.get("title", "")
    if title:
        layout.add_centered(title, bold=True)
    direction_code = metadata.get("direction_code", "")
    direction_name = metadata.get("direction_name", "")
    if direction_code or direction_name:
        layout.add_centered(f"по направлению {direction_code} {direction_name}".strip())
    layout.add_blank(1)
    supervisor = metadata.get("supervisor", "")
    if supervisor:
        layout.add_signatory("Руководитель", supervisor, title=metadata.get("supervisor_title"))
    reviewer = metadata.get("reviewer", "")
    if reviewer:
        layout.add_signatory("Рецензент", reviewer)
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
        layout.add_signatory("Выпускник", student)
    layout.add_blank(1)
    layout.add_footer(metadata)
