"""Form Н — РЕФЕРАТ / КОНТРОЛЬНАЯ / РГЗ / РГР / ЭССЕ."""
from __future__ import annotations
from typing import Any
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, resolve_document_type

FORM_ID = "form_n"
DEFAULT_DOCUMENT_TYPE = "РЕФЕРАТ"
REQUIRED_METADATA: tuple[str, ...] = ("title", "student", "group")
OPTIONAL_METADATA: tuple[str, ...] = (
    "document_type", "discipline", "teacher",
    "record_book", "institute", "department", "city", "year",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    layout.add_header(metadata)
    layout.add_blank(4)
    doc_type = resolve_document_type(metadata, DEFAULT_DOCUMENT_TYPE)
    layout.add_centered(doc_type, bold=True)
    discipline = metadata.get("discipline", "")
    if discipline:
        layout.add_centered(f"по дисциплине: {discipline}")
    title = metadata.get("title", "")
    if title:
        layout.add_centered(f"на тему: {title}")
    layout.add_blank(4)
    teacher = metadata.get("teacher", "")
    if teacher:
        layout.add_signatory("Преподаватель", teacher)
    student = metadata.get("student", "")
    group = metadata.get("group", "")
    record_book = metadata.get("record_book", "")
    if student:
        label = "Студент"
        if group:
            label = f"{label} {group}"
        if record_book:
            label = f"{label}, № {record_book}"
        layout.add_signatory(label, student)
    layout.add_blank(4)
    layout.add_footer(metadata)
