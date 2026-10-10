"""Registry loader and helpers.

Provides convenience accessors over the rule/profile collections and the
``build_legacy_config`` translator used by ``SIBFUConfig`` to keep its public
API stable while delegating values to the registry.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from sfu_converter.domain.formatting import (
    FormattingProfile,
    FormattingRule,
    RuleStatus,
)
from sfu_converter.registry.profiles import PROFILES
from sfu_converter.registry.rules import ALL_RULES, COMMON_RULES, RULES_BY_ID

_ALIGNMENT_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def iter_rules() -> Iterable[FormattingRule]:
    """Yield every registered rule."""

    return iter(ALL_RULES)


def iter_profiles() -> Iterable[FormattingProfile]:
    """Yield every registered profile."""

    return iter(PROFILES.values())


def get_rule(rule_id: str) -> FormattingRule:
    """Return the rule with ``rule_id`` or raise ``KeyError``."""

    return RULES_BY_ID[rule_id]


def get_profile(profile_name: str) -> FormattingProfile:
    """Return the profile with ``profile_name`` or raise ``KeyError``."""

    return PROFILES[profile_name]


def _params(rule_id: str) -> Mapping[str, object]:
    return RULES_BY_ID[rule_id].parameters


def _alignment(value: str):
    try:
        return _ALIGNMENT_MAP[value]
    except KeyError as exc:
        raise ValueError(f"Unknown alignment value: {value!r}") from exc


def _heading_block(rule_id: str) -> dict:
    params = _params(rule_id)
    return {
        "align": _alignment(params["alignment"]),
        "bold": bool(params["bold"]),
        "line_spacing": params["line_spacing"],
        "indent": Cm(params["indent_cm"]),
        "space_before": Pt(params["space_before_pt"]),
        "space_after": Pt(params["space_after_pt"]),
    }


def _spacing_block(rule_id: str) -> dict:
    params = _params(rule_id)
    return {
        "line_spacing": params["line_spacing"],
        "space_before": Pt(params["space_before_pt"]),
        "space_after": Pt(params["space_after_pt"]),
    }


def build_legacy_config() -> MutableMapping[str, object]:
    """Translate the registry into the dict the legacy ``SIBFUConfig`` exposes.

    Returns a mapping of attribute names to values that mirrors the historical
    ``SIBFUConfig`` shape so existing code (renderer, validator, image utils)
    keeps working without changes.
    """

    margins = _params("common.page.margins.portrait")
    image = _params("common.figure.image")
    page_numbering = _params("common.page.numbering")
    structural = _params("common.structural.heading")
    formula_body = _params("common.formula.body")
    return {
        "FONT_NAME": _params("common.text.font.name")["font_name"],
        "FONT_SIZE": Pt(_params("common.text.font.size")["font_size_pt"]),
        "FONT_COLOR_RGB": tuple(_params("common.text.font.color")["color_rgb"]),
        "LINE_SPACING_NORMAL": _params("common.text.line_spacing")["spacing"],
        "ALIGNMENT": _alignment(_params("common.text.alignment")["alignment"]),
        "FIRST_LINE_INDENT": Cm(_params("common.text.indent.first_line")["indent_cm"]),
        "H1": _heading_block("common.heading.h1"),
        "H2": _heading_block("common.heading.h2"),
        "H3": _heading_block("common.heading.h3"),
        "H4": _heading_block("common.heading.h4"),
        "LIST_ITEM": _heading_block("common.list.item"),
        "STRUCTURAL_SECTION": {
            "align": _alignment(structural["alignment"]),
            "bold": bool(structural["bold"]),
            "line_spacing": structural["line_spacing"],
            "indent": Cm(structural["indent_cm"]),
            "space_before": Pt(structural["space_before_pt"]),
            "space_after": Pt(structural["space_after_pt"]),
            "uppercase": bool(structural["uppercase"]),
            "page_break_before": bool(structural["page_break_before"]),
        },
        "STRUCTURAL_HEADINGS": tuple(structural["headings"]),
        "CAPTION_IMAGE": _heading_block("common.figure.caption"),
        "CAPTION_TABLE": _heading_block("common.table.caption"),
        "EMPTY_BEFORE_HEADER": _spacing_block("common.heading.spacing_before"),
        "EMPTY_AFTER_HEADER": _spacing_block("common.heading.spacing_after"),
        "EMPTY_BEFORE_IMAGE": _spacing_block("common.figure.spacing_before"),
        "EMPTY_AFTER_IMAGE": _spacing_block("common.figure.spacing_after"),
        "EMPTY_BEFORE_TABLE": _spacing_block("common.table.spacing_before"),
        "EMPTY_AFTER_TABLE": _spacing_block("common.table.spacing_after"),
        "EMPTY_BEFORE_FORMULA": _spacing_block("common.formula.spacing_before"),
        "EMPTY_AFTER_FORMULA": _spacing_block("common.formula.spacing_after"),
        "FORMULA": {
            **_heading_block("common.formula.body"),
            "number_tab_pos": Cm(formula_body["number_tab_pos_cm"]),
        },
        "FORMULA_EXPLANATION": _heading_block("common.formula.explanation"),
        "BIBLIOGRAPHY_ENTRY": _heading_block("common.bibliography.entry"),
        "MARGINS": {
            "top": Cm(margins["top_mm"] / 10),
            "bottom": Cm(margins["bottom_mm"] / 10),
            "left": Cm(margins["left_mm"] / 10),
            "right": Cm(margins["right_mm"] / 10),
        },
        "PAGE_NUMBERING": {
            "position": page_numbering["position"],
            "font_name": page_numbering["font_name"],
            "font_size": Pt(page_numbering["font_size_pt"]),
            "format": page_numbering["format"],
            "skip_first_page": bool(page_numbering["skip_first_page"]),
        },
        "IMAGE": {
            "line_spacing": image["line_spacing"],
            "alignment": _alignment(image["alignment"]),
            "width": Cm(image["max_width_cm"]),
            "height": None,
            "dpi": tuple(image["dpi"]),
            "format": image["format"],
            "max_width": Cm(image["max_width_cm"]),
        },
        "TABLE_CELL_PADDING": Pt(_params("common.table.cell_padding")["padding_pt"]),
        "TABLE": _table_block(),
    }


def _table_block() -> dict:
    body = _params("common.table.body")
    cell_padding = _params("common.table.cell_padding")
    return {
        "font_size": Pt(body["font_size_pt"]),
        "header_font_size": Pt(body["header_font_size_pt"]),
        "header_bold": bool(body["header_bold"]),
        "line_spacing": body["line_spacing"],
        "header_repeat_on_pages": bool(body["header_repeat_on_pages"]),
        "cell_padding": Pt(cell_padding["padding_pt"]),
    }


def rules_with_status(
    *,
    renderer: RuleStatus | None = None,
    validator: RuleStatus | None = None,
) -> list[FormattingRule]:
    """Filter rules by renderer/validator implementation status."""

    selected = []
    for rule in ALL_RULES:
        if renderer is not None and rule.renderer_status is not renderer:
            continue
        if validator is not None and rule.validator_status is not validator:
            continue
        selected.append(rule)
    return selected
