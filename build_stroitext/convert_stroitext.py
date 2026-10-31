#!/usr/bin/env python3
"""Convert the Obsidian Markdown 'Видение проекта СтройТекст' to SFU V2 TXT."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path("/home/cytr/obsidian_backup/Универ/МИСПИСИТ/Видение проекта СтройТекст. МИСПИСИТ.md")
DST = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/stroitext_v2.txt")

META = [
    ("document_type", "ОТЧЕТ О ПРАКТИЧЕСКОЙ РАБОТЕ №2"),
    (
        "title",
        "Исследование предметной области. Выявление и спецификация требований к информационной системе",
    ),
    ("student", "К. Д. Буданов"),
    ("group", "КИ23-14Б"),
    ("record_book", "032319377"),
    ("teacher", "М. О. Кузнецов"),
    ("institute", "Космических и информационных технологий"),
    ("department", "Информационные системы и технологии"),
    ("city", "Красноярск"),
    ("year", "2026"),
]

SOURCES = [
    "Система менеджмента качества. Общие требования к построению, изложению и оформлению документов учебной деятельности : СТУ 7.5–07–2021. — Красноярск, 2021.",
    "CommonMark Spec. Version 0.31.2. — 2024. — URL: https://spec.commonmark.org/0.31.2/ (дата обращения: 26.09.2026).",
    "ISO 32000-2:2020. Document management — Portable document format — Part 2: PDF 2.0. — 2nd ed. — Geneva : International Organization for Standardization, 2020.",
    "Nielsen, J. Response Times: The 3 Important Limits. — 1993. — URL: https://www.nngroup.com/articles/response-times-3-important-limits/ (дата обращения: 26.09.2026).",
    "О персональных данных : Федеральный закон от 27.07.2006 № 152-ФЗ. — URL: http://pravo.gov.ru/proxy/ips/?docbody&nd=102108261 (дата обращения: 26.09.2026).",
]

# In-text cross-reference fixes after renumbering (Введение is structural -> unnumbered).
REF_FIXES = [
    ("раздел 3.3", "раздел 2.3"),
    ("разделах 7 и 8", "разделах 6 и 7"),
    ("«Приложение 1. Глоссарий проекта»", "«Приложение А»"),
    ("«Приложение 2. Параметры профиля оформления»", "«Приложение Б»"),
]

# Headings whose level must be promoted (source nests them inconsistently).
PROMOTE_TO_H1 = {"Показатели качества"}

APPENDIX_HEADS = {
    "Приложение 1. Глоссарий проекта": ("app:glossary", "А", "ПРИЛОЖЕНИЕ А. ГЛОССАРИЙ ПРОЕКТА"),
    "Приложение 2. Параметры профиля оформления": (
        "app:profile",
        "Б",
        "ПРИЛОЖЕНИЕ Б. ПАРАМЕТРЫ ПРОФИЛЯ ОФОРМЛЕНИЯ",
    ),
}

# First-cell values that mark a 2-column key/value table (no real header row).
KV_FIRST_CELLS = {"Проблема", "Для", "**Типичный представитель**"}

# Captions for the key/value tables that have no ": caption" line in the
# source. Kept in document order.
KV_CAPTIONS = [
    "Постановка проблемы: ручное оформление учебных документов",
    "Постановка проблемы: повторное форматирование при изменении содержимого",
    "Постановка проблемы: единообразие оформления элементов",
    "Постановка проблемы: повторная настройка оформления под стандарт",
    "Постановка проблемы: ручная поддержка нумерации",
    "Постановка проблемы: поддержка собственных решений автоматизации",
    "Постановка проблемы: отсутствие институционального знания норм оформления",
    "Определение позиции изделия",
]
_kv_caption_index = [0]

STRUCTURAL_HEADS = {
    "Введение": "ВВЕДЕНИЕ",
}


def split_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [c.strip() for c in raw.split("|")]


def is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells if c.strip() != "") and any(
        c.strip() for c in cells
    )


def esc(text: str) -> str:
    return text.replace('"', "'")


def strip_emphasis(text: str) -> str:
    """List items are plain text in V2, so drop md markers."""
    return re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)


def table_cell(text: str) -> str:
    """Keep ``**bold**`` in table cells: the renderer turns it into a bold run."""
    return re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", text)


def fix_refs(text: str) -> str:
    for old, new in REF_FIXES:
        text = text.replace(old, new)
    return text.replace("---", "—")


def emit_table(rows: list[list[str]], caption: str | None, out: list[str]) -> None:
    body = [r for r in rows if not is_separator(r)]
    if not body:
        return
    width = max(len(r) for r in body)
    body = [r + [""] * (width - len(r)) for r in body]
    header = body[0][0].strip() not in KV_FIRST_CELLS
    if not header and not caption:
        if _kv_caption_index[0] < len(KV_CAPTIONS):
            caption = KV_CAPTIONS[_kv_caption_index[0]]
        _kv_caption_index[0] += 1
    attrs = []
    if caption:
        attrs.append(f'caption="{esc(caption)}"')
    if not header:
        attrs.append("header=false")
    out.append("[TABLE" + (" " + " ".join(attrs) if attrs else "") + "]")
    for r in body:
        out.append("| " + " | ".join(fix_refs(table_cell(c)) for c in r) + " |")
    out.append("[TABLE_END]")


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    out.append("[DOC syntax=2 profile=lab_practical_project_reports language=ru]")
    for key, value in META:
        out.append(f'[META key={key} value="{esc(value)}"]')
    out.append("")
    out.append("[TITLE_PAGE]")
    out.append("")
    out.append('[STRUCTURAL title="СОДЕРЖАНИЕ"]')

    i = 0
    in_appendix = False
    sources_emitted = False
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Markdown table + optional ": caption" line right after it.
        if stripped.startswith("|"):
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            caption = None
            if i < n and lines[i].strip().startswith(": "):
                caption = lines[i].strip()[2:].strip()
                i += 1
            emit_table(rows, caption, out)
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            title = title.rstrip("#").strip()
            if title in APPENDIX_HEADS:
                if not sources_emitted:
                    out.append("")
                    out.append('[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]')
                    for number, entry in enumerate(SOURCES, start=1):
                        out.append(f"[SOURCE number={number}] {entry}")
                    sources_emitted = True
                app_id, letter, full_title = APPENDIX_HEADS[title]
                out.append("")
                out.append(
                    f'[APPENDIX id={app_id} letter="{letter}" title="{esc(full_title)}"]'
                )
                in_appendix = True
                i += 1
                continue
            if title in STRUCTURAL_HEADS:
                out.append("")
                out.append(f'[STRUCTURAL title="{STRUCTURAL_HEADS[title]}"]')
                i += 1
                continue
            if title in PROMOTE_TO_H1:
                level = 1
            level = min(level, 4)
            out.append("")
            if in_appendix:
                out.append(f'[H level={level} title="{esc(title)}"]')
            else:
                out.append(f'[H level={level} title="{esc(title)}" number=auto]')
            i += 1
            continue

        # Bullet list
        if re.match(r"^[-*]\s+", stripped):
            out.append("")
            out.append("[LIST type=bullet]")
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                out.append(f"[-] {strip_emphasis(fix_refs(item))}")
                i += 1
            out.append("[LIST_END]")
            continue

        # Paragraph (join consecutive non-empty plain lines)
        parts = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if not nxt or nxt.startswith("|") or re.match(r"^#{1,6}\s", nxt) or re.match(r"^[-*]\s+", nxt):
                break
            parts.append(nxt)
            i += 1
        out.append("")
        out.append("[P] " + fix_refs(" ".join(parts)))

    text = "\n".join(out).rstrip() + "\n"
    DST.write_text(text, encoding="utf-8")
    print(f"Wrote {DST} ({len(text)} chars, {text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
