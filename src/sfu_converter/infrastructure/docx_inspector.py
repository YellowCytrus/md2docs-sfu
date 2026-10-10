from __future__ import annotations

from pathlib import Path
from typing import Iterable

from docx import Document as DocxDocument
from docx.document import Document as DocxDocumentType
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from sfu_converter.infrastructure import docx_styles


def dump(document: DocxDocumentType | str | Path, *, stop_at_page_break: bool = False) -> str:
    """Return a stable text dump of visible DOCX structure.

    The dump is intentionally narrow: enough for golden tests to catch renderer
    drift without depending on volatile Word XML.
    """

    doc = DocxDocument(str(document)) if isinstance(document, (str, Path)) else document
    lines: list[str] = []
    section_index = 1
    table_index = 0

    lines.append(_section_line(doc, section_index))
    for element in doc.element.body.iterchildren():
        if element.tag == qn("w:p"):
            paragraph = Paragraph(element, doc)
            if _style_name(paragraph) == docx_styles.METADATA:
                continue
            if stop_at_page_break and _has_page_break(paragraph):
                if paragraph.text.strip() or _image_descriptions(paragraph):
                    lines.extend(_paragraph_lines(paragraph))
                break
            lines.extend(_paragraph_lines(paragraph))
            if _has_section_break(paragraph):
                section_index += 1
                lines.append(_section_line(doc, section_index))
        elif element.tag == qn("w:tbl"):
            table_index += 1
            lines.extend(_table_lines(Table(element, doc), table_index))

    return "\n".join(lines) + "\n"


def _section_line(document: DocxDocumentType, section_index: int) -> str:
    try:
        section = document.sections[section_index - 1]
    except IndexError:
        return f"SECTION {section_index}"

    return (
        f"SECTION {section_index}: "
        f"orientation={section.orientation} "
        f"size={_cm(section.page_width)}x{_cm(section.page_height)}cm "
        f"margins={_cm(section.top_margin)}/{_cm(section.right_margin)}/"
        f"{_cm(section.bottom_margin)}/{_cm(section.left_margin)}cm"
    )


def _paragraph_lines(paragraph: Paragraph) -> list[str]:
    lines = [f'P style="{_style_name(paragraph)}" text="{_escaped(paragraph.text)}"']
    for run in paragraph.runs:
        lines.append(
            f'  R text="{_escaped(run.text)}" '
            f"bold={_flag(run.bold)} italic={_flag(run.italic)} "
            f"underline={_flag(run.underline)} font={_value(run.font.name)} "
            f"size={_font_size(run)}"
        )
    for image in _image_descriptions(paragraph):
        lines.append(
            f'  IMAGE name="{_escaped(image["name"])}" '
            f'title="{_escaped(image["title"])}" alt="{_escaped(image["alt"])}"'
        )
    return lines


def _table_lines(table: Table, table_index: int) -> list[str]:
    lines = [f'TABLE {table_index} style="{_style_name(table)}"']
    for row_index, row in enumerate(table.rows, start=1):
        cells = [_escaped(_cell_text(cell.text)) for cell in row.cells]
        lines.append(f"  ROW {row_index}: {cells!r}")
    return lines


def _image_descriptions(paragraph: Paragraph) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for element in paragraph._p.iter():
        if not str(element.tag).endswith("}docPr"):
            continue
        images.append(
            {
                "name": element.get("name", ""),
                "title": element.get("title", ""),
                "alt": element.get("descr", ""),
            }
        )
    return images


def _has_page_break(paragraph: Paragraph) -> bool:
    for element in paragraph._p.iter():
        if element.tag == qn("w:br") and element.get(qn("w:type")) == "page":
            return True
        if element.tag == qn("w:lastRenderedPageBreak"):
            return True
    return False


def _has_section_break(paragraph: Paragraph) -> bool:
    ppr = paragraph._p.pPr
    return ppr is not None and ppr.sectPr is not None


def _style_name(obj) -> str:
    style = getattr(obj, "style", None)
    return getattr(style, "name", "") or ""


def _font_size(run) -> str:
    size = run.font.size
    return "" if size is None else f"{size.pt:g}"


def _flag(value) -> str:
    return "1" if value else "0"


def _value(value) -> str:
    return "" if value is None else str(value)


def _cm(value) -> str:
    return f"{value.cm:.2f}"


def _cell_text(text: str) -> str:
    return " ".join((text or "").split())


def _escaped(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace('"', '\\"')
