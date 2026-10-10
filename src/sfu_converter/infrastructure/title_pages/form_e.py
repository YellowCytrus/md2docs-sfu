"""Form Е — VKR continuation page (consultants + norm controller)."""
from __future__ import annotations
from typing import Any
from sfu_converter.infrastructure.title_pages.base import TitlePageLayout, SIGNATURE_LINE

FORM_ID = "form_e"
DEFAULT_DOCUMENT_TYPE = ""
REQUIRED_METADATA: tuple[str, ...] = ("title",)
OPTIONAL_METADATA: tuple[str, ...] = (
    "consultants", "norm_controller",
)


def render(layout: TitlePageLayout, metadata: dict[str, Any]) -> None:
    title = metadata.get("title", "")
    if title:
        layout.add_centered(title, bold=True)
    layout.add_blank(2)
    consultants = metadata.get("consultants", "")
    if consultants:
        layout.add_centered("Консультанты по разделам:", bold=True)
        if isinstance(consultants, str):
            for line in consultants.split(";"):
                line = line.strip()
                if line:
                    layout.add_signatory("Консультант", line)
    layout.add_blank(2)
    norm_controller = metadata.get("norm_controller", "")
    if norm_controller:
        layout.add_signatory("Нормоконтролёр", norm_controller)
    layout.add_blank(2)
