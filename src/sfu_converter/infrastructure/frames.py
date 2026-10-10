from __future__ import annotations

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def draw(document, section) -> None:
    sect_pr = section._sectPr
    existing = sect_pr.find(qn("w:pgBorders"))
    if existing is not None:
        sect_pr.remove(existing)

    borders = OxmlElement("w:pgBorders")
    borders.set(qn("w:offsetFrom"), "page")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    sect_pr.append(borders)


def has_frame(document) -> bool:
    return any("w:pgBorders" in section._sectPr.xml for section in document.sections)
