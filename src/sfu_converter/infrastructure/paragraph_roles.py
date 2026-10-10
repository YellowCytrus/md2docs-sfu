"""Classify ``python-docx`` paragraphs into roles for the validator (Task 05).

The validator routes each paragraph to a rule family based on its role. Without
classification, every body-text rule is applied to figure captions, formula
bodies, bibliography entries, etc., which generates spurious diagnostics. The
classifier inspects style names first and falls back to regex heuristics on the
visible text so the validator works on documents produced before the renderer
started attaching SFU-prefixed styles (Task 06).

Classification is read-only: nothing here mutates ``python-docx`` state.
"""

from __future__ import annotations

import re
from enum import Enum, auto
from typing import Iterable

from sfu_converter.domain.formatting import FormattingProfile
from sfu_converter.infrastructure import docx_styles


class ParagraphRole(Enum):
    BODY = auto()
    HEADING_H1 = auto()
    HEADING_H2 = auto()
    HEADING_H3 = auto()
    HEADING_H4 = auto()
    STRUCTURAL_HEADING = auto()
    TOC_HEADING = auto()
    TOC_ENTRY = auto()
    TABLE_CAPTION = auto()
    TABLE_UNIT = auto()
    FIGURE_CAPTION = auto()
    FIGURE_EXPLANATORY = auto()
    FIGURE_PLACEHOLDER = auto()
    LIST_ITEM = auto()
    FORMULA_BODY = auto()
    FORMULA_EXPLANATION = auto()
    BIBLIOGRAPHY_ENTRY = auto()
    FOOTNOTE_TEXT = auto()
    APPENDIX_HEADING = auto()
    PAGE_NUMBER = auto()
    UNKNOWN = auto()


_TABLE_CAPTION_RE = re.compile(r"^\s*(Таблица|Продолжение таблицы|Окончание таблицы)\s+")
_FIGURE_CAPTION_RE = re.compile(r"^\s*Рисунок\s+")
_HEADING_NUMBERED_RE = re.compile(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?\s+\S")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[аА-яА-Я]\)|\d+\)|[-—–])\s")
_PLACEHOLDER_RE = re.compile(r"^\s*\[\s*(?:Изображение|Image|Ошибка)")
_TOC_PLACEHOLDER_RE = re.compile(r"^\s*Обновите оглавление\b", re.IGNORECASE)
_BIBLIOGRAPHY_RE = re.compile(r"^\s*\d+\.\s+\S")
_FORMULA_EXPLANATION_RE = re.compile(r"^\s*где\b")
_APPENDIX_HEADING_RE = re.compile(r"^\s*ПРИЛОЖЕНИЕ\b")
_STRUCTURAL_HEADINGS = {
    "РЕФЕРАТ",
    "АННОТАЦИЯ",
    "СОДЕРЖАНИЕ",
    "ВВЕДЕНИЕ",
    "ЗАКЛЮЧЕНИЕ",
    "СПИСОК СОКРАЩЕНИЙ",
    "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
}


_ROLE_BY_SFU_STYLE = {
    docx_styles.STRUCTURAL_HEADING: ParagraphRole.STRUCTURAL_HEADING,
    docx_styles.TOC_HEADING: ParagraphRole.TOC_HEADING,
    docx_styles.TABLE_CAPTION: ParagraphRole.TABLE_CAPTION,
    docx_styles.TABLE_UNIT: ParagraphRole.TABLE_UNIT,
    docx_styles.FIGURE_CAPTION: ParagraphRole.FIGURE_CAPTION,
    docx_styles.FIGURE_EXPLANATORY: ParagraphRole.FIGURE_EXPLANATORY,
    docx_styles.FIGURE_PLACEHOLDER: ParagraphRole.FIGURE_PLACEHOLDER,
    docx_styles.FORMULA_BODY: ParagraphRole.FORMULA_BODY,
    docx_styles.FORMULA_EXPLANATION: ParagraphRole.FORMULA_EXPLANATION,
    docx_styles.BIBLIOGRAPHY_ENTRY: ParagraphRole.BIBLIOGRAPHY_ENTRY,
    docx_styles.FOOTNOTE_TEXT: ParagraphRole.FOOTNOTE_TEXT,
    docx_styles.LIST_ITEM: ParagraphRole.LIST_ITEM,
    docx_styles.APPENDIX_HEADING: ParagraphRole.APPENDIX_HEADING,
}


def classify(
    paragraph,
    *,
    prev=None,
    next=None,
    table_context: bool = False,
    figure_context: bool = False,
    profile: FormattingProfile | None = None,
) -> ParagraphRole:
    """Return the role of ``paragraph`` using style + text heuristics."""

    style_name = _style_name(paragraph)
    text = paragraph.text or ""
    stripped = text.strip()

    role = _classify_by_word_style(style_name)
    if role is not None:
        return role

    role = _ROLE_BY_SFU_STYLE.get(style_name)
    if role is not None:
        return role

    if not stripped:
        return ParagraphRole.BODY

    if _APPENDIX_HEADING_RE.match(stripped):
        return ParagraphRole.APPENDIX_HEADING

    if stripped.upper() in _STRUCTURAL_HEADINGS:
        return ParagraphRole.STRUCTURAL_HEADING

    if _TABLE_CAPTION_RE.match(stripped):
        return ParagraphRole.TABLE_CAPTION

    if _FIGURE_CAPTION_RE.match(stripped):
        return ParagraphRole.FIGURE_CAPTION

    if _PLACEHOLDER_RE.match(stripped):
        return ParagraphRole.FIGURE_PLACEHOLDER

    if _TOC_PLACEHOLDER_RE.match(stripped):
        return ParagraphRole.TOC_ENTRY

    if _FORMULA_EXPLANATION_RE.match(stripped):
        return ParagraphRole.FORMULA_EXPLANATION

    if _LIST_ITEM_RE.match(stripped):
        return ParagraphRole.LIST_ITEM

    if _is_centered_bold_uppercase(paragraph):
        # Renderer's structural-heading shape: centered, bold, uppercase.
        return ParagraphRole.STRUCTURAL_HEADING

    if _is_centered_bold(paragraph):
        return ParagraphRole.HEADING_H1

    heading_match = _HEADING_NUMBERED_RE.match(stripped)
    if heading_match:
        depth = sum(1 for group in heading_match.groups() if group is not None)
        return {
            1: ParagraphRole.HEADING_H1,
            2: ParagraphRole.HEADING_H2,
            3: ParagraphRole.HEADING_H3,
            4: ParagraphRole.HEADING_H4,
        }[depth]

    return ParagraphRole.BODY


def classify_document(paragraphs: Iterable, **kwargs) -> list[ParagraphRole]:
    """Convenience helper: classify each paragraph in document order."""

    paragraphs = list(paragraphs)
    roles: list[ParagraphRole] = []
    for index, paragraph in enumerate(paragraphs):
        prev = paragraphs[index - 1] if index else None
        nxt = paragraphs[index + 1] if index + 1 < len(paragraphs) else None
        roles.append(classify(paragraph, prev=prev, next=nxt, **kwargs))
    return roles


def _style_name(paragraph) -> str:
    style = getattr(paragraph, "style", None)
    if style is None:
        return ""
    return getattr(style, "name", "") or ""


def _classify_by_word_style(style_name: str) -> ParagraphRole | None:
    if style_name.startswith("Heading 1"):
        return ParagraphRole.HEADING_H1
    if style_name.startswith("Heading 2"):
        return ParagraphRole.HEADING_H2
    if style_name.startswith("Heading 3"):
        return ParagraphRole.HEADING_H3
    if style_name.startswith("Heading 4"):
        return ParagraphRole.HEADING_H4
    if style_name.startswith("TOC "):
        return ParagraphRole.TOC_ENTRY
    if style_name == "Caption":
        return ParagraphRole.FIGURE_CAPTION
    return None


def _is_centered_bold_uppercase(paragraph) -> bool:
    if not _is_centered_bold(paragraph):
        return False
    text = (paragraph.text or "").strip()
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    return all(ch.isupper() for ch in letters)


def _is_centered_bold(paragraph) -> bool:
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    pf = paragraph.paragraph_format
    if pf.alignment != WD_ALIGN_PARAGRAPH.CENTER:
        return False
    runs = list(paragraph.runs)
    if not runs or not any(run.bold for run in runs):
        return False
    return bool((paragraph.text or "").strip())
