"""Form Л — Отчёт о НИР магистранта (Master's research-work report)."""
from __future__ import annotations
from typing import Any
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, resolve_document_type

FORM_ID = "form_l"
DEFAULT_DOCUMENT_TYPE = "ОТЧЕТ О НАУЧНО-ИССЛЕДОВАТЕЛЬСКОЙ РАБОТЕ"
REQUIRED_METADATA: tuple[str, ...] = ("title", "student", "group")
OPTIONAL_METADATA: tuple[str, ...] = (
    "document_type", "master_program", "program_head",
    "approval_date", "supervisor", "record_book",
    "institute", "department", "city", "year",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    layout.add_header(metadata)
    layout.add_blank(2)
    program_head = metadata.get("program_head", "")
    if program_head:
        layout.add_right("УТВЕРЖДАЮ")
        master_program = metadata.get("master_program", "")
        if master_program:
            layout.add_right(f"Руководитель магистерской программы")
            layout.add_right(master_program)
        layout.add_signatory("", program_head)
        approval_date = metadata.get("approval_date", "«___» _____________ 20__ г.")
        layout.add_right(approval_date)
    layout.add_blank(2)
    doc_type = resolve_document_type(metadata, DEFAULT_DOCUMENT_TYPE)
    layout.add_centered(doc_type, bold=True)
    title = metadata.get("title", "")
    if title:
        layout.add_centered(f"на тему: {title}")
    layout.add_blank(4)
    supervisor = metadata.get("supervisor", "")
    if supervisor:
        layout.add_signatory("Научный руководитель", supervisor, title=metadata.get("supervisor_title"))
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
    layout.add_blank(2)
    layout.add_footer(metadata)
