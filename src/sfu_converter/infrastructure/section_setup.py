from __future__ import annotations

from docx.enum.section import WD_ORIENT
from docx.shared import Cm

from sfu_converter.domain.ast_nodes import SectionOrientation, SectionSetupNode, SheetFormat


_SHEET_SIZES_CM = {
    SheetFormat.A4: (21.0, 29.7),
    SheetFormat.A3: (29.7, 42.0),
    SheetFormat.A3X4: (118.8, 42.0),
    SheetFormat.A4X4: (84.0, 29.7),
    SheetFormat.A2: (42.0, 59.4),
    SheetFormat.A1: (59.4, 84.1),
}

_TEXT_SECTION_WIDTH_LIMIT = Cm(22)
_TEXT_SECTION_HEIGHT_LIMIT = Cm(31)


def configure(document, section, node: SectionSetupNode) -> None:
    width_cm, height_cm = _SHEET_SIZES_CM[node.sheet_format]
    if node.orientation is SectionOrientation.LANDSCAPE:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Cm(max(width_cm, height_cm))
        section.page_height = Cm(min(width_cm, height_cm))
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)
        section.top_margin = Cm(3)
        section.bottom_margin = Cm(1)
        return

    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(min(width_cm, height_cm))
    section.page_height = Cm(max(width_cm, height_cm))
    section.left_margin = Cm(3)
    section.right_margin = Cm(1)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)


def requires_text_section_reset(section) -> bool:
    return (
        section.orientation != WD_ORIENT.PORTRAIT
        or section.page_width > _TEXT_SECTION_WIDTH_LIMIT
        or section.page_height > _TEXT_SECTION_HEIGHT_LIMIT
    )
