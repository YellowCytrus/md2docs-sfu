"""Form К — Отчёт о практике (Practice report)."""
from __future__ import annotations
from typing import Any
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, resolve_document_type

FORM_ID = "form_k"
DEFAULT_DOCUMENT_TYPE = "ОТЧЕТ О ПРАКТИКЕ"
REQUIRED_METADATA: tuple[str, ...] = ("title", "student", "group")
OPTIONAL_METADATA: tuple[str, ...] = (
    "document_type", "practice_place", "practice_kind",
    "university_supervisor", "enterprise_supervisor",
    "record_book", "institute", "department", "city", "year",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    layout.add_header(metadata)
    layout.add_blank(4)
    doc_type = resolve_document_type(metadata, DEFAULT_DOCUMENT_TYPE)
    layout.add_centered(doc_type, bold=True)
    title = metadata.get("title", "")
    if title:
        layout.add_centered(f"на тему: {title}")
    practice_place = metadata.get("practice_place", "")
    if practice_place:
        layout.add_centered(f"Место прохождения практики: {practice_place}")
    layout.add_blank(4)
    university_supervisor = metadata.get("university_supervisor", "")
    supervisor = metadata.get("supervisor", "")
    effective_supervisor = university_supervisor or supervisor
    if effective_supervisor:
        layout.add_signatory("Руководитель от университета", effective_supervisor)
    enterprise_supervisor = metadata.get("enterprise_supervisor", "")
    if enterprise_supervisor:
        layout.add_signatory("Руководитель от предприятия", enterprise_supervisor)
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
