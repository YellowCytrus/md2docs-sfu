#!/usr/bin/env python3
"""obsidian2sfu — Obsidian Markdown -> SFU-formatted DOCX.

Pipeline:  note.md (+ attachments)  ->  note.txt (V2 syntax)  ->  note.docx
The DOCX gets the SFU title page (from title_reference.docx), a real Word TOC
field, section-based table numbering and Times New Roman 14pt everywhere.

Run it with the project venv (needs python-docx):

    <project>/.venv/bin/python obsidian2sfu.py "note.md"

Config is merged from (lowest to highest priority):
    ~/.config/sfu/obsidian2sfu.json
    <note>.sfu.json            (same folder as the note)
    command-line options
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import unquote

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


def _config_dir() -> Path:
    """Config folder: %APPDATA%/sfu on Windows, ~/.config/sfu elsewhere."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "sfu"
    return Path.home() / ".config" / "sfu"


TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_TITLE = TOOL_DIR / "title_reference.docx"
DEFAULT_CONFIG = _config_dir() / "obsidian2sfu.json"
DEFAULT_VAULT = Path.home() / "obsidian_backup"
# `sfu-converter` is invoked via the same interpreter by default (works on
# Windows and Linux alike); override with --converter if needed.
DEFAULT_CONVERTER = None

STRUCTURAL_TITLES = {
    "введение": "ВВЕДЕНИЕ",
    "реферат": "РЕФЕРАТ",
    "аннотация": "АННОТАЦИЯ",
    "заключение": "ЗАКЛЮЧЕНИЕ",
    "содержание": "СОДЕРЖАНИЕ",
    "список сокращений": "СПИСОК СОКРАЩЕНИЙ",
    "список использованных источников": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
    "список источников": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
    "список литературы": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
    "библиография": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
}
APPENDIX_LETTERS = "АБВГДЕЖИКЛМНПРСТУФХЦЧШЩЭЮЯ"

# Reference title page values (from title_reference.docx) and the metadata key
# that overrides each one.  `None` means "build from several metadata keys".
TITLE_REFERENCE_DEFAULTS = {
    "institute": "Космических и информационных технологий",
    "department": "Систем искусственного интеллекта",
    "work_type": "ОТЧЁТ О ПРАКТИЧЕСКОЙ РАБОТЕ №1",
    "theme": "«Выявление высокоуровневых требований»",
    "teacher": "Петров П. П.",
    "group_id": "КИ00-00/0, 000000000",
    "student": "Иванов И. И.",
    "city_year": "Красноярск 2026",
}

DEFAULT_META = {
    "document_type": "ОТЧЁТ О ПРАКТИЧЕСКОЙ РАБОТЕ №1",
    "title": "Выявление высокоуровневых требований",
    "student": "Иванов И. И.",
    "group": "КИ00-00",
    "record_book": "000000000",
    "teacher": "Петров П. П.",
    "institute": "Космических и информационных технологий",
    "department": "Систем искусственного интеллекта",
    "city": "Красноярск",
    "year": "2026",
    "profile": "lab_practical_project_reports",
    "language": "ru",
}


# ======================================================================
#  Markdown -> V2 TXT
# ======================================================================

def _esc(value: str) -> str:
    return value.replace('"', "'")


def _strip_emphasis(text: str) -> str:
    return re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)


def _inline(text: str) -> str:
    """Normalise inline markdown for [P] (em dashes, __bold__, `code`->italic)."""
    text = re.sub(r"__(.+?)__", r"**\1**", text)
    text = re.sub(r"`([^`]+)`", r"*\1*", text)
    return text.replace("---", "—")


def _plain(text: str) -> str:
    """For table cells / list items (V2 keeps those as plain text)."""
    return _strip_emphasis(_inline(text).replace("`", ""))


def _split_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [c.strip() for c in raw.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells if c.strip() != ""
    ) and any(c.strip() for c in cells)


def _parse_frontmatter(lines: list[str]) -> tuple[dict, int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0
    for i in range(1, min(len(lines), 200)):
        if lines[i].strip() == "---":
            meta = {}
            for raw in lines[1:i]:
                if ":" in raw:
                    key, _, value = raw.partition(":")
                    meta[key.strip()] = value.strip().strip('"').strip("'")
            return meta, i + 1
    return {}, 0


class MarkdownConverter:
    def __init__(self, config: dict):
        self.cfg = config
        self.kv_first_cells = set(config.get("kv_first_cells", []))
        self.kv_captions = list(config.get("kv_captions", []))
        self.kv_index = 0
        self.ref_fixes = [tuple(pair) for pair in config.get("ref_fixes", [])]
        self.promote_h1 = set(config.get("promote_to_h1", []))
        self.sources = list(config.get("sources", []))
        self.image_map: dict[str, Path] = {}
        self.figures = 0
        vault = Path(config.get("vault", DEFAULT_VAULT)).expanduser()
        self.search_dirs = [vault, vault / config.get("attachment_folder", "attachments")]

    def fix(self, text: str) -> str:
        for old, new in self.ref_fixes:
            text = text.replace(old, new)
        return text.replace("---", "—")

    # -- images -------------------------------------------------------
    def _register_image(self, target: str, source_dir: Path) -> str | None:
        target = unquote(target).strip()
        base = Path(target).name
        candidates = [source_dir / target, source_dir / base]
        for folder in (source_dir.parent, source_dir.parent.parent):
            candidates += [folder / target, folder / base]
        for folder in self.search_dirs:
            candidates += [folder / target, folder / base, folder / target.replace(" ", "_"), folder / base.replace(" ", "_")]
        for candidate in candidates:
            if candidate.exists():
                self.figures += 1
                safe = re.sub(r"\s+", "_", candidate.name)
                self.image_map[safe] = candidate.resolve()
                return safe
        return None

    def _figure(self, out: list[str], target: str, caption: str, source_dir: Path) -> None:
        safe = self._register_image(target, source_dir)
        if not safe:
            out.append(f"[P] [Изображение не найдено: {target}]")
            return
        attrs = [f'src="{_esc(safe)}"']
        if caption:
            attrs.append(f'caption="{_esc(caption)}"')
        attrs.append(f"id=fig:{self.figures}")
        out.append("")
        out.append("[FIGURE " + " ".join(attrs) + "]")

    # -- tables -------------------------------------------------------
    def emit_table(self, rows: list[list[str]], caption: str | None, out: list[str]) -> None:
        body = [r for r in rows if not _is_separator(r)]
        if not body:
            return
        width = max(len(r) for r in body)
        body = [r + [""] * (width - len(r)) for r in body]
        header = body[0][0].strip() not in self.kv_first_cells
        attrs = []
        if not header and not caption:
            if self.kv_index < len(self.kv_captions):
                caption = self.kv_captions[self.kv_index]
            self.kv_index += 1
        if caption:
            attrs.append(f'caption="{_esc(caption)}"')
        if not header:
            attrs.append("header=false")
            if not caption:
                attrs.append("number=0")
        out.append("")
        out.append("[TABLE" + (" " + " ".join(attrs) if attrs else "") + "]")
        for r in body:
            out.append("| " + " | ".join(self.fix(_plain(c)) for c in r) + " |")
        out.append("[TABLE_END]")

    # -- formulas -----------------------------------------------------
    def emit_formula(self, out: list[str], latex: str) -> None:
        content = latex.strip()
        if not content:
            return
        out.append("")
        out.append("[FORMULA format=latex number=auto]")
        out.append(content)
        out.append("[FORMULA_END]")

    def try_display_math(self, lines: list[str], i: int, out: list[str]) -> int | None:
        """Emit ``$$...$$`` display math as numbered LaTeX formulas.

        Returns the next line index to resume from, or ``None`` when the current
        line is not display math. Inline ``$...$`` is intentionally left for the
        converter to render as inline equations.
        """

        stripped = lines[i].strip()
        if "$$" not in stripped:
            return None

        # Multi-line block: opening ``$$`` without a closing one on the same line.
        if stripped.startswith("$$") and stripped.count("$$") == 1:
            parts = [stripped[2:].strip()]
            j = i + 1
            while j < len(lines) and "$$" not in lines[j]:
                parts.append(lines[j].strip())
                j += 1
            if j >= len(lines):
                return None
            before, _, _ = lines[j].partition("$$")
            parts.append(before.strip())
            self.emit_formula(out, " ".join(p for p in parts if p))
            return j + 1

        # One or several ``$$...$$`` on a single line, possibly with text around.
        segments = re.split(r"\$\$(.+?)\$\$", stripped)
        if len(segments) == 1:
            return None
        for index, segment in enumerate(segments):
            if index % 2 == 1:
                self.emit_formula(out, segment)
            elif segment.strip():
                out.append("")
                out.append("[P] " + _inline(self.fix(segment.strip())))
        return i + 1

    # -- sources ------------------------------------------------------
    def emit_sources(self, out: list[str]) -> None:
        if not self.sources:
            return
        out.append("")
        out.append('[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]')
        for number, entry in enumerate(self.sources, start=1):
            out.append(f"[SOURCE number={number}] {self.fix(entry)}")

    # -- main ---------------------------------------------------------
    def convert(self, text: str, source_dir: Path) -> str:
        lines = text.splitlines()
        front, start = _parse_frontmatter(lines)
        out: list[str] = []
        profile = self.cfg["meta"].get("profile", "lab_practical_project_reports")
        language = self.cfg["meta"].get("language", "ru")
        out.append(f"[DOC syntax=2 profile={profile} language={language}]")
        for key, value in self.cfg["meta_items"]:
            out.append(f'[META key={key} value="{_esc(value)}"]')
        out.append("")
        out.append("[TITLE_PAGE]")
        out.append("")
        out.append('[STRUCTURAL title="СОДЕРЖАНИЕ"]')

        in_appendix = False
        sources_done = False
        appendix_index = 0
        i = start
        n = len(lines)
        while i < n:
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                continue

            # fenced code
            if stripped.startswith("```"):
                out.append("")
                out.append("[RAW]")
                i += 1
                while i < n and not lines[i].strip().startswith("```"):
                    out.append(lines[i])
                    i += 1
                i += 1
                out.append("[RAW_END]")
                continue

            # display math  $$...$$  -> numbered LaTeX formula
            display_math_end = self.try_display_math(lines, i, out)
            if display_math_end is not None:
                i = display_math_end
                continue

            # image on its own line  ![[file|caption]] or ![caption](path)
            m = re.match(r"^!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]$", stripped)
            if m:
                self._figure(out, m.group(1).strip(), (m.group(2) or "").strip(), source_dir)
                i += 1
                continue
            m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
            if m:
                self._figure(out, m.group(2).strip(), m.group(1).strip(), source_dir)
                i += 1
                continue

            # table
            if stripped.startswith("|"):
                rows = []
                while i < n and lines[i].strip().startswith("|"):
                    rows.append(_split_row(lines[i]))
                    i += 1
                caption = None
                look = i
                while look < n and not lines[look].strip():
                    look += 1
                if look < n and lines[look].strip().startswith(": "):
                    caption = lines[look].strip()[2:].strip()
                    i = look + 1
                self.emit_table(rows, caption, out)
                continue

            # heading
            m = re.match(r"^(#{1,6})\s+(.*?)\s*$", stripped)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip().rstrip("#").strip()
                key = " ".join(title.split()).casefold()
                appendix = re.match(r"(?i)^приложение\s+\d+[.\s]*(.*)$", title)
                if appendix:
                    if not sources_done:
                        self.emit_sources(out)
                        sources_done = True
                    letter = APPENDIX_LETTERS[min(appendix_index, len(APPENDIX_LETTERS) - 1)]
                    appendix_index += 1
                    rest = appendix.group(1).strip(" .")
                    full = f"ПРИЛОЖЕНИЕ {letter}." + (f" {rest.upper()}" if rest else "")
                    out.append("")
                    out.append(f'[APPENDIX id=app:{letter.lower()} letter="{letter}" title="{_esc(full)}"]')
                    in_appendix = True
                    i += 1
                    continue
                if key in STRUCTURAL_TITLES:
                    out.append("")
                    out.append(f'[STRUCTURAL title="{STRUCTURAL_TITLES[key]}"]')
                    i += 1
                    continue
                if title in self.promote_h1:
                    level = 1
                level = min(level, 4)
                out.append("")
                if in_appendix:
                    out.append(f'[H level={level} title="{_esc(title)}"]')
                else:
                    out.append(f'[H level={level} title="{_esc(title)}" number=auto]')
                i += 1
                continue

            # bullet list
            if re.match(r"^[-*+]\s+", stripped):
                out.append("")
                out.append("[LIST type=bullet]")
                while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                    item = re.sub(r"^[-*+]\s+", "", lines[i].strip())
                    out.append(f"[-] {_plain(self.fix(item))}")
                    i += 1
                out.append("[LIST_END]")
                continue

            # numbered list
            if re.match(r"^\d+[.)]\s+", stripped):
                out.append("")
                out.append("[LIST type=numbered]")
                while i < n and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                    item = re.sub(r"^\d+[.)]\s+", "", lines[i].strip())
                    out.append(f"[1)] {_plain(self.fix(item))}")
                    i += 1
                out.append("[LIST_END]")
                continue

            # blockquote -> paragraph
            if stripped.startswith(">"):
                text_line = stripped.lstrip(">").strip()
                out.append("")
                out.append("[P] " + _inline(self.fix(text_line)))
                i += 1
                continue

            # horizontal rule -> skip
            if re.fullmatch(r"[-*_]{3,}", stripped):
                i += 1
                continue

            # paragraph (join following plain lines)
            parts = [stripped]
            i += 1
            while i < n:
                nxt = lines[i].strip()
                if (
                    not nxt
                    or nxt.startswith("|")
                    or nxt.startswith("```")
                    or nxt.startswith(">")
                    or re.match(r"^#{1,6}\s", nxt)
                    or re.match(r"^[-*+]\s+", nxt)
                    or re.match(r"^\d+[.)]\s+", nxt)
                    or re.match(r"^!\[", nxt)
                    or re.fullmatch(r"[-*_]{3,}", nxt)
                ):
                    break
                parts.append(nxt)
                i += 1
            out.append("")
            out.append("[P] " + _inline(self.fix(" ".join(parts))))

        # sources without appendices -> emit at the end
        if self.sources and not sources_done:
            self.emit_sources(out)

        return "\n".join(out).rstrip() + "\n"


# ======================================================================
#  DOCX finalisation
# ======================================================================

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
        run.text = run.text[:local_start] + (new if first else "") + run.text[local_end:]
        first = False
    return True


def build_title_page(title_template: Path, meta: dict) -> list:
    source = Document(str(title_template))
    replacements = [
        (TITLE_REFERENCE_DEFAULTS["institute"], meta.get("institute", TITLE_REFERENCE_DEFAULTS["institute"])),
        (TITLE_REFERENCE_DEFAULTS["department"], meta.get("department", TITLE_REFERENCE_DEFAULTS["department"])),
        (TITLE_REFERENCE_DEFAULTS["work_type"], meta.get("document_type", TITLE_REFERENCE_DEFAULTS["work_type"])),
        (TITLE_REFERENCE_DEFAULTS["theme"], f"«{meta.get('title', '')}»" if meta.get("title") else TITLE_REFERENCE_DEFAULTS["theme"]),
        (TITLE_REFERENCE_DEFAULTS["teacher"], meta.get("teacher", TITLE_REFERENCE_DEFAULTS["teacher"])),
        (TITLE_REFERENCE_DEFAULTS["group_id"], f"{meta.get('group', '')}, {meta.get('record_book', '')}".strip(", ")),
        (TITLE_REFERENCE_DEFAULTS["student"], meta.get("student", TITLE_REFERENCE_DEFAULTS["student"])),
        (TITLE_REFERENCE_DEFAULTS["city_year"], f"{meta.get('city', '')} {meta.get('year', '')}".strip()),
    ]

    for paragraph in source.paragraphs:
        if paragraph.text.strip().upper() == "СОДЕРЖАНИЕ":
            break
        for old, new in replacements:
            if old and new and old != new:
                _replace_across_runs(paragraph, old, new)

    body = source.element.body
    sect_pr = body.find(qn("w:sectPr"))
    elements = []
    for child in list(body):
        if child is sect_pr:
            continue
        if child.tag == qn("w:p"):
            text = "".join(t.text or "" for t in child.findall(".//" + qn("w:t"))).strip()
            if text.upper() == "СОДЕРЖАНИЕ":
                break
        elements.append(child)

    for element in elements:
        for br in element.findall(".//" + qn("w:br")):
            if br.get(qn("w:type")) == "page":
                br.getparent().remove(br)

    # drop one spacer line before the signature so the title still fits one page
    for index, element in enumerate(elements):
        if element.tag != qn("w:p"):
            continue
        text = "".join(t.text or "" for t in element.findall(".//" + qn("w:t")))
        if text.strip().startswith("Преподаватель"):
            back = index - 1
            while back >= 0 and elements[back].tag == qn("w:p"):
                prev = "".join(t.text or "" for t in elements[back].findall(".//" + qn("w:t")))
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


def replace_title_page(doc: Document, title_template: Path, meta: dict) -> None:
    body = doc.element.body
    children = list(body)
    first_break = next((el for el in children if _is_page_break_only(el)), None)
    for el in children:
        body.remove(el)
        if el is first_break:
            break
    for el in reversed(build_title_page(title_template, meta)):
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
        return []
    entries = []
    for para in paragraphs[start:]:
        text = para.text
        if "\t" in text and re.search(r"\t\d+", text):
            entries.append(para)
        elif entries and text.strip():
            break
    return entries


def ensure_toc_dot_leaders(doc: Document) -> None:
    for para in toc_entries(doc):
        pf = para.paragraph_format
        if pf.tab_stops:
            pos = pf.tab_stops[0].position
            pf.tab_stops.clear_all()
            pf.tab_stops.add_tab_stop(pos, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)


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
    entries = toc_entries(doc)
    if not entries:
        return
    anchor = entries[0]._p.find(qn("w:pPr"))
    for element in (
        _field_run("begin"),
        _instruction_run(' TOC \\o "1-3" \\h \\z \\u '),
        _field_run("separate"),
    ):
        anchor.addnext(element)
        anchor = element
    entries[-1]._p.append(_field_run("end"))


def renumber_appendix_captions(doc: Document) -> None:
    """Number tables and figures inside appendices as {letter}.{n}."""
    letter = None
    table_number = None
    table_counter = 0
    figure_counter = 0
    for para in doc.paragraphs:
        if para.style.name == "SFUAppendixHeading":
            match = re.match(r"ПРИЛОЖЕНИЕ\s+([А-ЯЁ])", para.text.strip())
            if match:
                letter = match.group(1)
                table_counter = 0
                figure_counter = 0
                table_number = None
            continue
        text = para.text.strip()
        if not letter:
            continue
        if text.startswith("Таблица "):
            table_counter += 1
            table_number = f"{letter}.{table_counter}"
            _set_paragraph_text(para, re.sub(r"^Таблица\s+\S+", f"Таблица {table_number}", text))
        elif text.startswith(("Продолжение таблицы", "Окончание таблицы")) and table_number:
            _set_paragraph_text(para, re.sub(r"таблицы\s+\S+", f"таблицы {table_number}", text, count=1))
        elif text.startswith("Рисунок "):
            figure_counter += 1
            _set_paragraph_text(
                para, re.sub(r"^Рисунок\s+\S+", f"Рисунок {letter}.{figure_counter}", text)
            )


def _set_paragraph_text(para, text: str) -> None:
    if para.runs:
        para.runs[0].text = text
        for run in para.runs[1:]:
            run.text = ""


# ======================================================================
#  Page-aware table splitting: Продолжение / Окончание таблицы N
# ======================================================================

_TABLE_CAPTION_RE = re.compile(r"^Таблица\s+([\w.]+)")
_CONTINUATION_RE = re.compile(r"^(?:Продолжение|Окончание)\s+таблицы\s+([\w.]+)\s*$")


def _caption_above(items, index):
    """Return ``(paragraph, number)`` of the caption/label above ``items[index]``."""

    for back in range(index - 1, max(index - 5, -1), -1):
        if items[back][0] != "p":
            continue
        text = items[back][1].text.strip()
        if not text:
            continue
        match = _CONTINUATION_RE.match(text) or _TABLE_CAPTION_RE.match(text)
        if match:
            return items[back][1], match.group(1)
    return None, None


def _has_bold_header(table) -> bool:
    if not table.rows:
        return False
    for cell in table.rows[0].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                if run.bold:
                    return True
    return False


def _uno_module():
    """Import ``uno`` from the system LibreOffice bindings, or ``None``.

    The virtualenv has no pyuno of its own, but the distro ships one built for
    the same CPython the venv runs. Prepending its directory lets us import it
    in-process without adding a dependency to the project.
    """

    try:
        import uno  # noqa: PLC0415

        return uno
    except ImportError:
        pass
    candidates = [
        Path("/usr/lib/python3/dist-packages"),
        *sorted(Path("/usr/lib").glob("python3*/site-packages")),
        *sorted(Path("/usr/lib").glob("python3*/dist-packages")),
    ]
    for directory in candidates:
        if (directory / "uno.py").exists():
            sys.path.insert(0, str(directory))
            try:
                import uno  # noqa: PLC0415

                return uno
            except ImportError:
                continue
    return None


def _layout_table_pages(docx_path: Path, port: int) -> dict[str, list[int]] | None:
    """Ask LibreOffice's layout engine for the real page of every table row.

    Returns ``{table_name: [page per row]}`` or ``None`` when the engine is
    unavailable. These are the numbers the engine actually paginated to — not an
    estimate — so a table is only ever split where it really does cross a page.
    """

    uno = _uno_module()
    if uno is None:
        return None

    from com.sun.star.beans import PropertyValue  # noqa: PLC0415

    soffice = _find_libreoffice()
    if soffice is None:
        return None

    def prop(name, value):
        item = PropertyValue()
        item.Name = name
        item.Value = value
        return item

    process = subprocess.Popen(
        [
            soffice,
            "--headless",
            "--norestore",
            "--invisible",
            f"--accept=socket,host=127.0.0.1,port={port};urp;",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    document = None
    desktop = None
    try:
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )
        url = f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
        context = None
        for _ in range(60):
            try:
                context = resolver.resolve(url)
                break
            except Exception:  # noqa: BLE001 - the socket may not be up yet
                time.sleep(0.5)
        if context is None:
            return None

        desktop = context.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", context
        )
        document = desktop.loadComponentFromURL(
            uno.systemPathToFileUrl(str(docx_path.resolve())),
            "_blank",
            0,
            (prop("Hidden", True), prop("ReadOnly", True)),
        )
        if document is None:
            return None

        cursor = document.CurrentController.getViewCursor()
        tables = document.getTextTables()
        layout: dict[str, list[int]] = {}
        for index in range(tables.getCount()):
            table = tables.getByIndex(index)
            rows = table.getRows()
            pages = []
            for row_index in range(rows.getCount()):
                cell = table.getCellByName(f"A{row_index + 1}")
                text_cursor = cell.getText().createTextCursor()
                text_cursor.gotoStart(False)
                cursor.gotoRange(text_cursor, False)
                pages.append(cursor.getPage())
            layout[table.getName()] = pages
        return layout
    except Exception:  # noqa: BLE001 - layout is best-effort
        return None
    finally:
        if document is not None:
            try:
                document.close(False)
            except Exception:  # noqa: BLE001
                pass
        if desktop is not None:
            try:
                desktop.terminate()
            except Exception:  # noqa: BLE001
                pass
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _clone_table_with_rows(template_tbl, rows):
    new_tbl = deepcopy(template_tbl)
    for tr in new_tbl.findall(qn("w:tr")):
        new_tbl.remove(tr)
    for tr in rows:
        new_tbl.append(deepcopy(tr))
    return new_tbl


def _add_continuation_caption(doc: Document, anchor, text: str):
    """Insert a continuation caption right after ``anchor``.

    The caption opens its own page (``pageBreakBefore``) and is bound to the
    table part that follows (``keep_with_next``), so the two can never be split
    across pages.
    """

    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    try:
        para.style = doc.styles["SFUTableCaption"]
    except KeyError:
        pass
    para.paragraph_format.page_break_before = True
    para.paragraph_format.keep_with_next = True
    anchor.addnext(para._p)
    return para


def _body_items(doc) -> list[tuple[str, object]]:
    """Body-level items as ``(kind, object)``: 'p' for paragraphs, 't' for tables."""

    from docx.table import Table
    from docx.text.paragraph import Paragraph

    items = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            items.append(("p", Paragraph(child, doc)))
        elif child.tag == qn("w:tbl"):
            items.append(("t", Table(child, doc)))
    return items


def _first_spanning_table(doc, row_pages: list[list[int]]) -> dict | None:
    """First captioned table whose rows the layout engine put on several pages.

    Only tables with a real ``Таблица N — ...`` caption participate; a title-page
    layout table has no such caption and is left alone. ``row_pages`` is the
    per-table row->page mapping produced by the engine, in document order.
    """

    items = _body_items(doc)
    for index, (kind, table) in enumerate(items):
        if kind != "t":
            continue
        caption_para, number = _caption_above(items, index)
        if caption_para is None or number is None:
            continue
        row_index = sum(1 for kind_, _ in items[:index] if kind_ == "t")
        if row_index >= len(row_pages):
            continue
        page_map = row_pages[row_index]
        if len(page_map) < 2 or max(page_map) <= min(page_map):
            continue
        text = caption_para.text.strip()
        return {
            "caption": text,
            "caption_paragraph": caption_para,
            "table": table,
            "number": number,
            "page_map": page_map,
            "continuation": _CONTINUATION_RE.match(text) is not None,
        }
    return None


def _split_spanning_table(doc, found: dict) -> bool:
    """Cut a table at the page boundary the layout engine actually produced."""

    table = found["table"]
    page_map = found["page_map"]
    header_count = 1 if _has_bold_header(table) else 0
    if len(page_map) <= header_count + 1:
        return False

    first_page = page_map[0]
    boundary = next(
        (index for index in range(header_count, len(page_map)) if page_map[index] > first_page),
        None,
    )
    trs = table._tbl.findall(qn("w:tr"))
    if boundary is None or boundary >= len(trs) or boundary <= header_count:
        return False

    header_rows = trs[:header_count]
    tbl = table._tbl
    for tr in list(trs):
        tbl.remove(tr)
    for tr in trs[:boundary]:
        tbl.append(tr)

    label = _add_continuation_caption(doc, tbl, f"Продолжение таблицы {found['number']}")
    new_tbl = _clone_table_with_rows(tbl, header_rows + trs[boundary:])
    label._p.addnext(new_tbl)
    return True


def reflow_tables(stage: Path, workdir: Path, max_passes: int = 40) -> None:
    """Split page-spanning tables, then repeat until every part fits a page.

    The split points are not estimated: each pass asks the LibreOffice layout
    engine (via pyuno) which page every table row actually landed on, and cuts
    at the first row that the engine moved to a later page. Because the engine
    knows the real geometry, a table is never cut speculatively and a part is
    never left straddling a page — the loop keeps going until the engine reports
    that every table sits on a single page. Continuation captions open their own
    page (``pageBreakBefore``), so the label and its part always belong
    together.
    """

    if _find_libreoffice() is None:
        return

    for pass_index in range(max_passes):
        row_pages = _layout_table_pages(stage, port=2100 + pass_index)
        if not row_pages:
            break
        row_pages = list(row_pages.values())
        doc = Document(str(stage))
        found = _first_spanning_table(doc, row_pages)
        if found is None:
            break
        if _split_spanning_table(doc, found):
            doc.save(str(stage))
            continue
        break

    finalize_table_captions(stage)


def normalize_continuation_labels(doc: Document) -> None:
    """The last part of every split table says 'Окончание', all earlier parts 'Продолжение'."""

    groups: dict[str, list] = {}
    for para in doc.paragraphs:
        match = _CONTINUATION_RE.match(para.text.strip())
        if match:
            groups.setdefault(match.group(1), []).append(para)
    for number, paras in groups.items():
        for para in paras[:-1]:
            _set_paragraph_text(para, f"Продолжение таблицы {number}")
        _set_paragraph_text(paras[-1], f"Окончание таблицы {number}")


def keep_caption_with_table(doc: Document) -> None:
    """A caption directly above a table must never be pushed to another page."""

    from docx.text.paragraph import Paragraph

    body = doc.element.body
    children = list(body.iterchildren())
    for index, child in enumerate(children):
        if child.tag != qn("w:p") or index + 1 >= len(children):
            continue
        if children[index + 1].tag != qn("w:tbl"):
            continue
        text = "".join(t.text or "" for t in child.findall(".//" + qn("w:t"))).strip()
        if _CONTINUATION_RE.match(text) or _TABLE_CAPTION_RE.match(text):
            Paragraph(child, doc).paragraph_format.keep_with_next = True


def finalize_table_captions(stage: Path) -> None:
    doc = Document(str(stage))
    normalize_continuation_labels(doc)
    keep_caption_with_table(doc)
    doc.save(str(stage))


def _find_libreoffice() -> str | None:
    for name in ("libreoffice", "soffice", "soffice.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def convert_pdf(docx: Path, outdir: Path) -> Path | None:
    soffice = _find_libreoffice()
    if not soffice:
        return None
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return outdir / (docx.stem + ".pdf")


def pdf_pages(pdf: Path) -> list[str]:
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True
    ).stdout
    return [p for p in text.split("\f") if p.strip()]


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def assign_pages(entries, pages: list[str]) -> dict[str, int]:
    body_start = None
    for i, page in enumerate(pages, start=1):
        if "ВВЕДЕНИЕ" in page:
            body_start = i
            break
    if body_start is None:
        body_start = 1
    normalized = [_norm(p) for p in pages]
    result: dict[str, int] = {}
    cursor = body_start
    for para in entries:
        heading = para.text.rsplit("\t", 1)[0].strip()
        needle = _norm(heading)
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


# ======================================================================
#  Driver
# ======================================================================

def load_config(md: Path, overrides: dict, extra_config: str | None = None) -> dict:
    cfg = {
        "meta": dict(DEFAULT_META),
        "title_template": str(DEFAULT_TITLE),
        "sources": [],
        "kv_first_cells": ["Проблема", "Для", "**Типичный представитель**"],
        "kv_captions": [],
        "ref_fixes": [],
        "promote_to_h1": [],
        "profile": "lab_practical_project_reports",
        "language": "ru",
    }
    config_paths = [DEFAULT_CONFIG, md.with_suffix(".sfu.json")]
    if extra_config:
        config_paths.append(Path(extra_config).expanduser())
    for path in config_paths:
        if path.exists():
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
    meta = cfg["meta"]
    front, _ = _parse_frontmatter(md.read_text(encoding="utf-8").splitlines())
    for key, value in front.items():
        meta.setdefault(key, value)
    for key, value in overrides.get("meta", {}).items():
        meta[key] = value
    cfg["profile"] = overrides.get("profile", cfg.get("profile", meta.get("profile", "lab_practical_project_reports")))
    cfg["language"] = cfg.get("language", meta.get("language", "ru"))
    if overrides.get("title_template"):
        cfg["title_template"] = overrides["title_template"]
    if overrides.get("sources_file"):
        entries = Path(overrides["sources_file"]).read_text(encoding="utf-8").splitlines()
        cfg["sources"] = [e.strip() for e in entries if e.strip()]
    # ordered META lines (skip non-title metadata keys)
    skip = {"profile", "language", "city", "year"}
    items = []
    for key, value in meta.items():
        if key in skip or not value:
            continue
        items.append((key, value))
    items.append(("city", meta.get("city", "Красноярск")))
    items.append(("year", meta.get("year", "2026")))
    cfg["meta_items"] = items
    return cfg


# sfu-converter exit codes (see sfu_converter.cli.ExitCodes).
CONVERTER_VALIDATION_ERROR = 2


def run_converter(converter, txt: Path, docx: Path, profile: str, workdir: Path) -> None:
    base = [converter] if converter else [sys.executable, "-m", "sfu_converter.cli"]
    cmd = base + [
        "convert",
        "--input", str(txt),
        "--output", str(docx),
        "--profile", profile,
        "--syntax-version", "2",
        "--workdir", str(workdir),
    ]
    # Drop a stale result so the exit-code handling below never accepts old output.
    docx.unlink(missing_ok=True)
    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        sys.exit(f"sfu-converter not found: {converter!r}; use --converter /path/to/sfu-converter")
    if result.returncode == 0:
        return
    # `convert` writes the DOCX first, then reports validation diagnostics; it
    # exits 2 (VALIDATION_ERROR) when the generated TXT has error-severity
    # issues even though the output is usable. Only treat that as fatal if no
    # document was actually produced.
    if result.returncode == CONVERTER_VALIDATION_ERROR and docx.exists():
        print(
            f"[3/4] sfu-converter reported validation issues for {txt.name} "
            f"(exit {result.returncode}); using the generated document anyway",
            file=sys.stderr,
        )
        return
    sys.exit(f"sfu-converter failed with exit code {result.returncode}: {' '.join(cmd)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Obsidian Markdown -> SFU DOCX")
    ap.add_argument("markdown", help="path to the .md note (relative names are looked up in the vault)")
    ap.add_argument("--vault", default=str(DEFAULT_VAULT))
    ap.add_argument("--out", default=None, help="output .docx path (default: next to the note)")
    ap.add_argument("--config", default=None, help="extra JSON config to merge")
    ap.add_argument("--title-template", default=None)
    ap.add_argument("--sources-file", default=None, help="file with one bibliography entry per line")
    ap.add_argument("--converter", default=DEFAULT_CONVERTER,
                    help="путь к sfu-converter (по умолчанию: python -m sfu_converter.cli)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override metadata")
    ap.add_argument("--no-pdf", action="store_true", help="do not build a preview PDF")
    args = ap.parse_args()

    md = Path(args.markdown).expanduser()
    if not md.is_absolute() and not md.exists():
        md = Path(args.vault).expanduser() / md
    if not md.exists():
        sys.exit(f"markdown not found: {md}")
    md = md.resolve()

    overrides: dict = {"meta": {}}
    for item in args.set:
        key, _, value = item.partition("=")
        overrides["meta"][key.strip()] = value.strip()
    if args.title_template:
        overrides["title_template"] = args.title_template
    if args.sources_file:
        overrides["sources_file"] = args.sources_file

    cfg = load_config(md, overrides, args.config)
    cfg["vault"] = str(Path(args.vault).expanduser())

    out_docx = Path(args.out).expanduser().resolve() if args.out else md.with_suffix(".docx")
    workdir = out_docx.parent
    workdir.mkdir(parents=True, exist_ok=True)
    txt_path = out_docx.with_suffix(".txt")

    raw_docx = workdir / (out_docx.stem + ".raw.docx")

    # 1. markdown -> V2 txt
    converter = MarkdownConverter(cfg)
    txt_path.write_text(converter.convert(md.read_text(encoding="utf-8"), md.parent), encoding="utf-8")
    print(f"[1/4] TXT written: {txt_path}")

    # 2. copy referenced images next to the output so the converter finds them
    images_dir = workdir / "images"
    if converter.image_map:
        images_dir.mkdir(exist_ok=True)
        for name, src in converter.image_map.items():
            shutil.copy2(src, images_dir / name)
        print(f"[2/4] {len(converter.image_map)} image(s) copied to {images_dir}")
    else:
        print("[2/4] no images")

    # 3. txt -> docx
    run_converter(args.converter, txt_path, raw_docx, cfg["profile"], workdir)
    print(f"[3/4] DOCX built: {raw_docx}")

    # 4. finalize: title page, ToC field, appendix tables
    doc = Document(str(raw_docx))
    replace_title_page(doc, Path(cfg["title_template"]), cfg["meta"])
    fix_consecutive_page_breaks(doc)
    remove_field_placeholder(doc)
    ensure_toc_dot_leaders(doc)
    stage = workdir / (out_docx.stem + ".stage.docx")
    doc.save(str(stage))

    # Split tables that run over a page boundary and label their continuations
    # ("Продолжение/Окончание таблицы N"); re-measure after every split.
    reflow_tables(stage, workdir)

    with_toc = None
    pdf = convert_pdf(stage, workdir)
    if pdf and (shutil.which("pdftotext")):
        pages = pdf_pages(pdf)
        doc = Document(str(stage))
        renumber_appendix_captions(doc)
        entries = toc_entries(doc)
        mapping = assign_pages(entries, pages)
        for para in entries:
            heading = para.text.rsplit("\t", 1)[0].strip()
            if para.runs:
                para.runs[-1].text = f"{heading}\t{mapping.get(para.text, 1)}"
        wrap_toc_in_field(doc)
        doc.save(str(out_docx))
        with_toc = True
        print(f"[4/4] DOCX finalized: {out_docx}")
    else:
        doc = Document(str(stage))
        renumber_appendix_captions(doc)
        wrap_toc_in_field(doc)
        doc.save(str(out_docx))
        print(f"[4/4] DOCX finalized (ToC without page numbers): {out_docx}")

    for leftover in (raw_docx, stage, stage.with_suffix(".pdf")):
        leftover.unlink(missing_ok=True)

    if not args.no_pdf:
        preview = convert_pdf(out_docx, workdir)
        if preview:
            print(f"PDF: {preview}")


if __name__ == "__main__":
    main()
