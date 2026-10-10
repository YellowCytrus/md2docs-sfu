#!/usr/bin/env python3
"""Finalize the SFU DOCX: replace title page, fix blank page, build accurate ToC."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_LEADER, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
COLOR = RGBColor(0, 0, 0)

TITLE_DATA = {
    "institute": "Космических и информационных технологий",
    "department": "Информационные системы и технологии",
    "work_type": "ОТЧЕТ О ПРАКТИЧЕСКОЙ РАБОТЕ №2",
    "theme": "Исследование предметной области. Выявление и спецификация требований к информационной системе",
    "teacher": "М. О. Кузнецов",
    "group": "КИ23-14Б",
    "student_id": "032319377",
    "student": "К. Д. Буданов",
    "city_year": "Красноярск 2026",
}


def normalize_continuation_labels(doc: Document) -> None:
    """Ensure each split table has 'Продолжение…' except its last page ('Окончание…')."""
    pattern = re.compile(r"^(Продолжение|Окончание) таблицы ([\d.]+)$")
    groups: dict[str, list] = {}
    for para in doc.paragraphs:
        match = pattern.match(para.text.strip())
        if match:
            groups.setdefault(match.group(2), []).append(para)
    for number, paras in groups.items():
        for para in paras[:-1]:
            if para.runs:
                para.runs[0].text = f"Продолжение таблицы {number}"
                for run in para.runs[1:]:
                    run.text = ""
        if paras[-1].runs:
            paras[-1].runs[0].text = f"Окончание таблицы {number}"
            for run in paras[-1].runs[1:]:
                run.text = ""


def _find_line_page(pages_lines: list[list[str]], needle: str, start: int):
    if len(needle) < 4:
        return None
    for index in range(start, len(pages_lines) + 1):
        for line in pages_lines[index - 1]:
            if line == needle or line.startswith(needle) or (len(line) >= 6 and needle.startswith(line)):
                return index
    return None


def renumber_appendix_tables(doc: Document) -> None:
    """Number tables inside appendices as {letter}.{n} instead of the last H1."""
    letter = None
    number = None
    counter = 0
    for para in doc.paragraphs:
        if para.style.name == "SFUAppendixHeading":
            match = re.match(r"ПРИЛОЖЕНИЕ\s+([А-ЯЁ])", para.text.strip())
            if match:
                letter = match.group(1)
                counter = 0
                number = None
            continue
        text = para.text.strip()
        if not letter:
            continue
        if text.startswith("Таблица "):
            counter += 1
            number = f"{letter}.{counter}"
            new_text = re.sub(r"^Таблица\s+\S+", f"Таблица {number}", text)
            _set_paragraph_text(para, new_text)
        elif text.startswith(("Продолжение таблицы", "Окончание таблицы")) and number:
            new_text = re.sub(r"таблицы\s+\S+", f"таблицы {number}", text, count=1)
            _set_paragraph_text(para, new_text)


def _set_paragraph_text(para, text: str) -> None:
    if para.runs:
        para.runs[0].text = text
        for run in para.runs[1:]:
            run.text = ""


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def _find_page(pages_norm: list[str], needle: str, start: int):
    if not needle:
        return None
    for index in range(start, len(pages_norm) + 1):
        if needle in pages_norm[index - 1]:
            return index
    return None


def _table_number(caption: str):
    match = re.search(r"(\d+(?:\.\d+)?)", caption)
    return match.group(1) if match else None


def _has_header(table) -> bool:
    first_row = table.rows[0]
    for cell in first_row.cells:
        for para in cell.paragraphs:
            for run in para.runs:
                if run.bold:
                    return True
    return False


def split_tables_at_page_breaks(stage: Path, pages: list[str]) -> int:
    import re as _re

    from docx.oxml.ns import qn as _qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(stage))
    body = doc.element.body
    pages_norm = [_norm(p) for p in pages]
    pages_lines = [[_norm(line) for line in page.splitlines()] for page in pages]

    items = []
    for child in body.iterchildren():
        if child.tag == _qn("w:p"):
            items.append(("p", Paragraph(child, doc)))
        elif child.tag == _qn("w:tbl"):
            items.append(("t", Table(child, doc)))

    splits = 0
    first_tbl = body.find(_qn("w:tbl"))
    for index, (kind, obj) in enumerate(items):
        if kind != "t":
            continue
        table = obj
        if table._tbl is first_tbl:  # title-page signature table
            continue
        caption = ""
        for back in range(index - 1, max(index - 4, -1), -1):
            if items[back][0] == "p":
                text = items[back][1].text.strip()
                if text:
                    caption = text
                    break
        caption_page = _find_page(pages_norm, _norm(caption), 1) or 1

        # Verify the table really spans pages: its last row must be on a later
        # page than the caption. Otherwise a stray text match would split a
        # table that actually fits, dropping the caption into its middle.
        last_row_cells = [
            c.text.strip() for c in table.rows[-1].cells if c.text.strip()
        ]
        last_page = None
        if last_row_cells:
            last_page = _find_page(
                pages_norm, _norm(max(last_row_cells, key=len)), caption_page
            )
        if last_page is None or last_page <= caption_page:
            continue

        cursor = caption_page
        page_map = []
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            page = None
            if cells:
                distinctive = max(cells, key=len)
                if len(distinctive) >= 15:
                    page = _find_page(pages_norm, _norm(distinctive), cursor)
            if page is not None:
                cursor = page
            page_map.append(page)

        # Rows with no reliable match inherit the next page when the table is
        # known to continue, otherwise the previous one (conservative: a row
        # that starts the continuation page must not stay in the first chunk).
        previous = caption_page
        for index in range(len(page_map)):
            if page_map[index] is not None:
                previous = page_map[index]
                continue
            following = None
            for candidate in page_map[index + 1 :]:
                if candidate is not None:
                    following = candidate
                    break
            page_map[index] = following if (following and following > previous) else previous

        # Clamp to the last row's page so a stray late match can't add a bogus
        # boundary beyond the real end of the table.
        page_map = [min(p, last_page) for p in page_map]

        number = _table_number(caption)
        header = _has_header(table)
        trs = table._tbl.findall(_qn("w:tr"))
        header_rows = trs[:1] if header else []

        boundaries = []
        previous = None
        for row_index, page in enumerate(page_map):
            if previous is not None and page is not None and page > previous:
                boundaries.append(row_index)
            if page is not None:
                previous = page
        boundaries = [b for b in boundaries if b > len(header_rows)]
        if not boundaries:
            continue

        # Build chunks split at each page boundary.
        chunks = []
        start = 0
        for boundary in boundaries:
            chunks.append(trs[start:boundary])
            start = boundary
        chunks.append(trs[start:])
        chunks = [c for c in chunks if c]

        tbl = table._tbl
        anchor = tbl
        for chunk_index, chunk in enumerate(chunks):
            if chunk_index == 0:
                # keep the original table element for the first chunk
                for tr in list(trs):
                    tbl.remove(tr)
                for tr in chunk:
                    tbl.append(tr)
                continue
            label = "Окончание" if chunk_index == len(chunks) - 1 else "Продолжение"
            caption_text = f"{label} таблицы {number}" if number else label
            para = doc.add_paragraph()
            run = para.add_run(caption_text)
            run.font.name = FONT
            run.font.size = Pt(14)
            para.style = doc.styles["SFUTableCaption"]
            para.paragraph_format.keep_with_next = True
            new_tbl = _clone_table_with_rows(tbl, header_rows + chunk)
            anchor.addnext(para._p)
            para._p.addnext(new_tbl)
            anchor = new_tbl
        doc.save(str(stage))
        return 1

    return 0


def fix_label_placement(stage: Path, pages: list[str]) -> int:
    """Roll back spurious splits: a continuation caption that is not the first
    line of its page means the table actually fit, so merge the chunks back."""
    from docx.table import Table

    doc = Document(str(stage))
    pages_norm = [_norm(p) for p in pages]
    first_lines = []
    for page in pages:
        first = ""
        for line in page.splitlines():
            if line.strip():
                first = _norm(line)
                break
        first_lines.append(first)

    prefixes = ("Продолжение таблицы", "Окончание таблицы")
    changed = 0
    for para in list(doc.paragraphs):
        text = para.text.strip()
        if not text.startswith(prefixes):
            continue
        page = _find_page(pages_norm, _norm(text), 1)
        if page is None:
            continue
        if first_lines[page - 1].startswith(_norm(text)[:18]):
            continue
        prev = para._p.getprevious()
        while prev is not None and prev.tag != qn("w:tbl"):
            prev = prev.getprevious()
        nxt = para._p.getnext()
        while nxt is not None and nxt.tag != qn("w:tbl"):
            nxt = nxt.getnext()
        if prev is None or nxt is None:
            continue
        prev_trs = prev.findall(qn("w:tr"))
        nxt_trs = nxt.findall(qn("w:tr"))
        header_count = 1 if _has_header(Table(nxt, doc)) else 0

        if len(prev_trs) <= header_count:
            continue
        last_tr = prev_trs[-1]
        if header_count > 0 and nxt_trs:
            nxt_trs[header_count - 1].addnext(last_tr)
        elif nxt_trs:
            nxt_trs[0].addprevious(last_tr)
        else:
            nxt.append(last_tr)
        changed += 1
    if changed:
        doc.save(str(stage))
    return changed


def _clone_table_with_rows(template_tbl, rows):
    from copy import deepcopy

    from docx.oxml.ns import qn as _qn

    new_tbl = deepcopy(template_tbl)
    for tr in new_tbl.findall(_qn("w:tr")):
        new_tbl.remove(tr)
    for tr in rows:
        new_tbl.append(deepcopy(tr))
    return new_tbl


# ---------- low-level helpers ----------

def _style_run(run, *, size: int = 14, bold: bool = False) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = COLOR
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)


def _para(doc, text="", *, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, bold=False,
          bottom_border=False, side_indent_cm=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Cm(0)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    if side_indent_cm is not None:
        pf.left_indent = Cm(side_indent_cm)
        pf.right_indent = Cm(side_indent_cm)
    if text:
        run = p.add_run(text)
        _style_run(run, size=size, bold=bold)
    if bottom_border:
        ppr = p._p.get_or_add_pPr()
        pbdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "2")
        bottom.set(qn("w:color"), "000000")
        pbdr.append(bottom)
        ppr.append(pbdr)
    return p


def _cell_bottom_border(cell) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "0")
    bottom.set(qn("w:color"), "000000")
    borders.append(bottom)
    tcpr.append(borders)


def _cell_text(cell, text, *, align=WD_ALIGN_PARAGRAPH.LEFT, size=14, bold=False,
               first=False):
    p = cell.paragraphs[0] if first else cell.add_paragraph()
    p.paragraph_format.alignment = align
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    if text:
        run = p.add_run(text)
        _style_run(run, size=size, bold=bold)
    return p


def _remove_all_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "auto")
        borders.append(el)
    tbl_pr.append(borders)


TITLE_TEMPLATE = Path("/home/cytr/Downloads/Telegram Desktop/Видение.docx")

TITLE_REPLACEMENTS = [
    ("КИ23-15/2Б, 032320965", "КИ23-14Б, 032319377"),
    ("Р. А. Лямин", "К. Д. Буданов"),
]


def _replace_across_runs(paragraph, old: str, new: str) -> bool:
    runs = paragraph.runs
    full = "".join(r.text for r in runs)
    index = full.find(old)
    if index < 0:
        return False
    end = index + len(old)
    position = 0
    first = True
    for run in runs:
        start, stop = position, position + len(run.text)
        position = stop
        if stop <= index or start >= end:
            continue
        local_start = max(index - start, 0)
        local_end = min(end - start, len(run.text))
        prefix = run.text[:local_start]
        suffix = run.text[local_end:]
        run.text = prefix + (new if first else "") + suffix
        first = False
    return True


def build_title_page() -> list:
    """Take the reference title page as a template and substitute the data."""
    source = Document(str(TITLE_TEMPLATE))
    for paragraph in source.paragraphs:
        if paragraph.text.strip().upper() == "СОДЕРЖАНИЕ":
            break
        for old, new in TITLE_REPLACEMENTS:
            _replace_across_runs(paragraph, old, new)

    body = source.element.body
    sect_pr = body.find(qn("w:sectPr"))
    elements = []
    for child in list(body):
        if child is sect_pr:
            continue
        if child.tag == qn("w:p"):
            text = "".join(
                t.text or "" for t in child.findall(".//" + qn("w:t"))
            ).strip()
            if text.upper() == "СОДЕРЖАНИЕ":
                break
        elements.append(child)

    # The reference title page carries its own trailing page break; our ToC
    # already starts a new page, so drop it to avoid a blank page.
    for element in elements:
        for br in element.findall(".//" + qn("w:br")):
            if br.get(qn("w:type")) == "page":
                br.getparent().remove(br)

    # Free one line: the title is right at the page height, so the ToC's page
    # break would otherwise spill to a blank page.
    for index, element in enumerate(elements):
        if element.tag != qn("w:p"):
            continue
        text = "".join(t.text or "" for t in element.findall(".//" + qn("w:t")))
        if text.strip().startswith("Преподаватель"):
            back = index - 1
            while back >= 0 and elements[back].tag == qn("w:p"):
                prev = "".join(
                    t.text or "" for t in elements[back].findall(".//" + qn("w:t"))
                )
                if prev.strip() == "":
                    elements.pop(back)
                    break
                back -= 1
            break
    return elements


def _is_page_break_only(el) -> bool:
    if el.tag != qn("w:p"):
        return False
    brs = [b for b in el.findall(".//" + qn("w:br")) if b.get(qn("w:type")) == "page"]
    text = "".join(t.text or "" for t in el.findall(".//" + qn("w:t")))
    return bool(brs) and not text.strip()


def replace_title_page(doc: Document) -> None:
    from copy import deepcopy

    body = doc.element.body
    children = list(body)
    first_break = next((el for el in children if _is_page_break_only(el)), None)
    for el in children:
        body.remove(el)
        if el is first_break:
            break
    for el in reversed(build_title_page()):
        body.insert(0, deepcopy(el))


def fix_consecutive_page_breaks(doc: Document) -> None:
    body = doc.element.body
    prev_break = False
    for para in list(body.findall(qn("w:p"))):
        is_break_only = _is_page_break_only(para)
        if is_break_only and prev_break:
            body.remove(para)
            continue
        prev_break = is_break_only


def remove_field_placeholder(doc: Document) -> None:
    for para in list(doc.paragraphs):
        if "Обновите оглавление" in para.text:
            para._element.getparent().remove(para._element)


def toc_entries(doc: Document):
    paragraphs = doc.paragraphs
    start = None
    for index, para in enumerate(paragraphs):
        if para.text.strip().upper() == "СОДЕРЖАНИЕ":
            start = index + 1
            break
    if start is None:
        return [p for p in paragraphs if p.style.name.startswith("TOC")]

    entries = []
    for para in paragraphs[start:]:
        text = para.text
        if "\t" in text and re.search(r"\t\d+", text):
            entries.append(para)
        elif entries and text.strip():
            break
    return entries


def _field_run(fld_type: str):
    run = OxmlElement("w:r")
    element = OxmlElement("w:fldChar")
    element.set(qn("w:fldCharType"), fld_type)
    run.append(element)
    return run


def _instruction_run(text: str):
    run = OxmlElement("w:r")
    element = OxmlElement("w:instrText")
    element.set(qn("xml:space"), "preserve")
    element.text = text
    run.append(element)
    return run


def wrap_toc_in_field(doc: Document) -> None:
    """Turn the generated contents list into a real Word TOC field.

    The entries become the cached field result, so Word shows them immediately
    and rebuilds them on Ctrl+A, F9.
    """
    entries = toc_entries(doc)
    if not entries:
        return
    first_p = entries[0]._p
    anchor = first_p.find(qn("w:pPr"))
    for element in (
        _field_run("begin"),
        _instruction_run(' TOC \\o "1-3" \\h \\z \\u '),
        _field_run("separate"),
    ):
        anchor.addnext(element)
        anchor = element
    entries[-1]._p.append(_field_run("end"))


def ensure_toc_dot_leaders(doc: Document) -> None:
    for para in toc_entries(doc):
        pf = para.paragraph_format
        if pf.tab_stops:
            pos = pf.tab_stops[0].position
            pf.tab_stops.clear_all()
            pf.tab_stops.add_tab_stop(pos, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)


def convert_pdf(docx: Path, outdir: Path) -> Path:
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return outdir / (docx.stem + ".pdf")


def pdf_pages(pdf: Path) -> list[str]:
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [p for p in text.split("\f") if p.strip()]


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def assign_pages(entries, pages: list[str]) -> dict[str, int]:
    body_start = None
    for i, page in enumerate(pages, start=1):
        if "ВВЕДЕНИЕ" in page:
            body_start = i
            break
    if body_start is None:
        body_start = 1
    normalized = [norm(p) for p in pages]
    result: dict[str, int] = {}
    cursor = body_start
    for para in entries:
        heading = para.text.rsplit("\t", 1)[0].strip()
        needle = norm(heading)
        found = None
        for page in range(cursor, len(pages) + 1):
            if needle and needle in normalized[page - 1]:
                found = page
                break
        if found is None:
            found = cursor
        result[para.text] = found
        cursor = found
    return result


def main() -> None:
    src = Path(sys.argv[1])
    final = Path(sys.argv[2])
    work = Path("/tmp/stroitext_finalize")
    work.mkdir(exist_ok=True)

    doc = Document(str(src))
    replace_title_page(doc)
    fix_consecutive_page_breaks(doc)
    remove_field_placeholder(doc)
    ensure_toc_dot_leaders(doc)
    stage = work / "stage.docx"
    doc.save(str(stage))

    # Stepwise: re-render after every split so each table's page boundaries are
    # measured on the up-to-date layout (no cascading errors).
    # Alternate splitting and rollback of spurious splits until stable.
    # Continuation captions proved unreliable (they could land mid-table), so
    # tables simply break between rows and repeat their header row instead.
    pdf = convert_pdf(stage, work)

    pdf = convert_pdf(stage, work)
    pages = pdf_pages(pdf)
    print(f"stage PDF pages: {len(pages)}")

    doc = Document(str(stage))
    normalize_continuation_labels(doc)
    renumber_appendix_tables(doc)
    entries = toc_entries(doc)
    mapping = assign_pages(entries, pages)
    for para in entries:
        heading = para.text.rsplit("\t", 1)[0].strip()
        page = mapping.get(para.text, 1)
        if para.runs:
            para.runs[-1].text = f"{heading}\t{page}"
    wrap_toc_in_field(doc)
    doc.save(str(final))
    print(f"wrote {final} with {len(entries)} ToC entries")

    preview = convert_pdf(final, work)
    print(f"preview PDF: {preview}")


if __name__ == "__main__":
    main()
