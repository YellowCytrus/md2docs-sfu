"""Idempotent custom paragraph styles used by the renderer (Task 06).

The validator (Task 05) reads ``paragraph.style.name`` to classify each
paragraph. Without distinct styles for figure captions, formula bodies,
bibliography entries, etc., classification has to fall back to brittle text
heuristics. ``register_styles`` attaches the SFU-prefixed styles to a document
once; subsequent calls are no-ops.
"""

from __future__ import annotations

from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor

from sfu_converter.config import SIBFUConfig
from sfu_converter.infrastructure.docx_measurements import FIRST_LINE_INDENT_CM, NO_INDENT_CM


STRUCTURAL_HEADING = "SFUStructuralHeading"
METADATA = "SFUMetadata"
FOOTNOTE_ANCHOR = "SFUFootnoteAnchor"
FOOTNOTE_TEXT = "SFUFootnoteText"
TABLE_CAPTION = "SFUTableCaption"
TABLE_UNIT = "SFUTableUnit"
TABLE = "SFUTable"
ABBREVIATIONS_TABLE = "SFUAbbreviationsTable"
FIGURE_CAPTION = "SFUFigureCaption"
FIGURE_EXPLANATORY = "SFUFigureExplanatory"
FIGURE_PLACEHOLDER = "SFUFigurePlaceholder"
FORMULA_BODY = "SFUFormulaBody"
FORMULA_EXPLANATION = "SFUFormulaExplanation"
BIBLIOGRAPHY_ENTRY = "SFUBibliographyEntry"
LIST_ITEM = "SFUListItem"
TOC_HEADING = "SFUTOCHeading"
APPENDIX_HEADING = "SFUAppendixHeading"
FRAME_MAIN_INSCRIPTION = "SFUFrameMainInscription"

ALL_SFU_STYLES: tuple[str, ...] = (
    STRUCTURAL_HEADING,
    METADATA,
    FOOTNOTE_ANCHOR,
    FOOTNOTE_TEXT,
    TABLE_CAPTION,
    TABLE_UNIT,
    TABLE,
    ABBREVIATIONS_TABLE,
    FIGURE_CAPTION,
    FIGURE_EXPLANATORY,
    FIGURE_PLACEHOLDER,
    FORMULA_BODY,
    FORMULA_EXPLANATION,
    BIBLIOGRAPHY_ENTRY,
    LIST_ITEM,
    TOC_HEADING,
    APPENDIX_HEADING,
    FRAME_MAIN_INSCRIPTION,
)


def register_styles(document) -> None:
    """Attach SFU paragraph styles to ``document``; safe to call repeatedly."""

    _set_document_default_font(document)

    _register(document, STRUCTURAL_HEADING, base="Normal", bold=True, all_caps=True,
              alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=NO_INDENT_CM,
              outline_level=0)
    _register(document, METADATA, base="Normal", hidden=True,
              first_line_indent=NO_INDENT_CM, line_spacing=1.0)
    _register_character(document, FOOTNOTE_ANCHOR, superscript=True, size=Pt(12))
    _register(document, FOOTNOTE_TEXT, base="Normal", size=Pt(12),
              alignment=WD_ALIGN_PARAGRAPH.LEFT, first_line_indent=NO_INDENT_CM,
              line_spacing=1.0)
    _register(document, TABLE_CAPTION, base="Caption",
              alignment=WD_ALIGN_PARAGRAPH.LEFT, first_line_indent=NO_INDENT_CM,
              line_spacing=1.0)
    _register(document, TABLE_UNIT, base="Normal", size=Pt(12),
              alignment=WD_ALIGN_PARAGRAPH.RIGHT, first_line_indent=NO_INDENT_CM)
    _register_table(document, TABLE)
    _register_table(document, ABBREVIATIONS_TABLE)
    _register(document, FIGURE_CAPTION, base="Caption",
              alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=NO_INDENT_CM,
              line_spacing=1.0)
    _register(document, FIGURE_EXPLANATORY, base="Normal", size=Pt(12),
              alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=NO_INDENT_CM,
              line_spacing=1.0)
    _register(document, FIGURE_PLACEHOLDER, base="Normal", italic=True,
              first_line_indent=NO_INDENT_CM)
    _register(document, FORMULA_BODY, base="Normal",
              alignment=WD_ALIGN_PARAGRAPH.LEFT, first_line_indent=FIRST_LINE_INDENT_CM,
              right_tab_pos=SIBFUConfig.FORMULA["number_tab_pos"])
    _register(document, FORMULA_EXPLANATION, base="Normal",
              alignment=WD_ALIGN_PARAGRAPH.LEFT, first_line_indent=NO_INDENT_CM)
    _register(document, BIBLIOGRAPHY_ENTRY, base="Normal",
              alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=FIRST_LINE_INDENT_CM)
    _register(document, LIST_ITEM, base="Normal",
              alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=FIRST_LINE_INDENT_CM)
    _register(document, TOC_HEADING, base=STRUCTURAL_HEADING, bold=True, all_caps=True,
              alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=NO_INDENT_CM)
    _register(document, APPENDIX_HEADING, base="Normal", bold=True,
              alignment=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=NO_INDENT_CM,
              outline_level=0)
    _register_table(document, FRAME_MAIN_INSCRIPTION)


def apply_word_heading_style(document, paragraph, style_name: str) -> None:
    """Attach a built-in Word heading style when the template provides it."""

    try:
        paragraph.style = document.styles[style_name]
    except KeyError:
        return


def _set_document_default_font(document) -> None:
    """Make Times New Roman 14 pt the document default.

    Without this, unstyled paragraphs (spacing blocks, empty cells) inherit the
    python-docx default Calibri 11 pt, which shows up as stray 11 pt lines.
    """
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(14)
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.paragraph_format.line_spacing = 1.0
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), "Times New Roman")

    # Any template default (docDefaults) wins for paragraph marks, so fix it too.
    styles_element = document.styles.element
    defaults = styles_element.find(qn("w:docDefaults"))
    if defaults is not None:
        rpr_default = defaults.find(qn("w:rPrDefault"))
        if rpr_default is not None:
            rpr = rpr_default.find(qn("w:rPr"))
            if rpr is not None:
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.insert(0, rfonts)
                for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                    rfonts.set(qn(attr), "Times New Roman")
                    rfonts.attrib.pop(qn(attr + "Theme"), None)
                size = rpr.find(qn("w:sz"))
                if size is None:
                    size = OxmlElement("w:sz")
                    rpr.append(size)
                size.set(qn("w:val"), "28")

        ppr_default = defaults.find(qn("w:pPrDefault"))
        if ppr_default is not None:
            ppr = ppr_default.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                ppr_default.append(ppr)
            spacing = ppr.find(qn("w:spacing"))
            if spacing is None:
                spacing = OxmlElement("w:spacing")
                ppr.insert(0, spacing)
            spacing.set(qn("w:line"), "240")
            spacing.set(qn("w:lineRule"), "auto")
            spacing.set(qn("w:after"), "0")


def _register(
    document,
    name: str,
    *,
    base: str = "Normal",
    bold: bool = False,
    italic: bool = False,
    all_caps: bool = False,
    alignment=None,
    first_line_indent=None,
    size=None,
    hidden: bool = False,
    right_tab_pos=None,
    outline_level: int | None = None,
    line_spacing=None,
) -> None:
    styles = document.styles
    if name in [s.name for s in styles]:
        return

    style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    if base in [s.name for s in styles]:
        style.base_style = styles[base]

    font = style.font
    font.name = "Times New Roman"
    font.size = size or Pt(14)
    font.bold = bold
    font.italic = italic
    font.hidden = hidden
    font.color.rgb = RGBColor(0, 0, 0)
    if all_caps:
        font.all_caps = True

    pf = style.paragraph_format
    if alignment is not None:
        pf.alignment = alignment
    if first_line_indent is not None:
        pf.first_line_indent = first_line_indent
    if right_tab_pos is not None:
        pf.tab_stops.add_tab_stop(Emu(int(right_tab_pos)), WD_TAB_ALIGNMENT.RIGHT)
    if line_spacing is not None:
        pf.line_spacing = line_spacing
    if outline_level is not None:
        _set_outline_level(style, outline_level)


def _register_character(
    document,
    name: str,
    *,
    superscript: bool = False,
    size=None,
) -> None:
    styles = document.styles
    if name in [s.name for s in styles]:
        return

    style = styles.add_style(name, WD_STYLE_TYPE.CHARACTER)
    font = style.font
    font.name = "Times New Roman"
    font.size = size or Pt(14)
    font.color.rgb = RGBColor(0, 0, 0)
    font.superscript = superscript


def _register_table(document, name: str) -> None:
    styles = document.styles
    if name in [s.name for s in styles]:
        return

    style = styles.add_style(name, WD_STYLE_TYPE.TABLE)
    font = style.font
    font.name = "Times New Roman"
    font.color.rgb = RGBColor(0, 0, 0)


def _set_outline_level(style, level: int) -> None:
    p_pr = style.element.get_or_add_pPr()
    existing = p_pr.find(qn("w:outlineLvl"))
    if existing is not None:
        p_pr.remove(existing)

    outline = OxmlElement("w:outlineLvl")
    outline.set(qn("w:val"), str(level))
    p_pr.append(outline)
