"""Tests for the data-driven paragraph format dispatch in DocxRenderer."""

from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from sfu_converter.config import SIBFUConfig
from sfu_converter.infrastructure.docx_renderer import DocxRenderer


ALL_STYLE_TYPES = (
    "normal",
    "h1",
    "h2",
    "h3",
    "h4",
    "list_item",
    "structural_section",
    "toc_heading",
    "appendix_heading",
    "caption_img",
    "figure_explanatory",
    "caption_table",
    "table_unit",
    "empty_before_header",
    "empty_after_header",
    "empty_before_image",
    "empty_after_image",
    "empty_before_table",
    "empty_after_table",
    "empty_before_formula",
    "empty_after_formula",
    "formula",
    "formula_explanation",
    "bibliography_entry",
)


def _make_renderer(tmp_path):
    renderer = DocxRenderer(config_class=SIBFUConfig, base_dir=tmp_path)
    renderer.doc = Document()
    return renderer


def _new_para(renderer, text="Sample"):
    return renderer.doc.add_paragraph(text)


def test_style_map_covers_every_known_style(tmp_path):
    renderer = _make_renderer(tmp_path)
    assert set(renderer._style_map) == set(ALL_STYLE_TYPES)


def test_every_style_can_be_applied_without_error(tmp_path):
    renderer = _make_renderer(tmp_path)
    for style_type in ALL_STYLE_TYPES:
        para = _new_para(renderer, style_type)
        renderer._set_paragraph_format(para, style_type)
        assert para.runs, f"{style_type}: paragraph has no runs after formatting"


def test_normal_style_applies_justified_alignment_and_indent(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "normal")
    pf = para.paragraph_format

    assert pf.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert pf.line_spacing == 1.5
    assert abs(pf.first_line_indent - Cm(1.25)) < 1000
    assert pf.space_before == Pt(0)
    assert pf.space_after == Pt(0)


def test_heading_styles_are_left_aligned_with_body_indent(tmp_path):
    renderer = _make_renderer(tmp_path)

    for style_type in ("h1", "h2", "h3", "h4"):
        para = _new_para(renderer, style_type)
        renderer._set_paragraph_format(para, style_type)
        pf = para.paragraph_format

        assert pf.alignment == WD_ALIGN_PARAGRAPH.LEFT
        assert pf.line_spacing == 1.0
        assert abs(pf.first_line_indent - Cm(1.25)) < 1000
    assert renderer.doc.paragraphs[-4].runs[0].bold is True


def test_h2_style_is_bold(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "h2")

    assert para.runs[0].bold is True


def test_h3_style_is_not_bold(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "h3")

    assert para.runs[0].bold is False


def test_list_item_style_matches_body_indent_and_spacing(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "list_item")
    pf = para.paragraph_format

    assert pf.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert pf.line_spacing == 1.5
    assert abs(pf.first_line_indent - Cm(1.25)) < 1000
    assert pf.space_before == Pt(0)
    assert pf.space_after == Pt(0)
    assert para.runs[0].bold is False


def test_structural_section_style_centered_bold_no_indent(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "structural_section")
    pf = para.paragraph_format

    assert pf.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert pf.line_spacing == 1.0
    assert abs(pf.first_line_indent - Cm(0)) < 1000
    assert para.runs[0].bold is True


def test_caption_table_style_left_aligned(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "caption_table")

    assert para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.LEFT


def test_caption_img_style_centered(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "caption_img")

    assert para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_empty_before_image_uses_zero_indent(tmp_path):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    renderer._set_paragraph_format(para, "empty_before_image")

    assert abs(para.paragraph_format.first_line_indent - Cm(0)) < 1000
    assert para.paragraph_format.line_spacing == 0.8


def test_unknown_style_logs_warning_and_skips(tmp_path, caplog):
    renderer = _make_renderer(tmp_path)
    para = _new_para(renderer)

    with caplog.at_level("WARNING", logger="sfu_converter.infrastructure.docx_renderer"):
        renderer._set_paragraph_format(para, "no_such_style")

    assert any("Unknown style_type" in rec.getMessage() for rec in caplog.records)


def test_style_map_is_built_once_per_renderer(tmp_path):
    renderer = _make_renderer(tmp_path)
    first = renderer._style_map
    second = renderer._style_map
    assert first is second
