"""Tests for the formatting rule registry."""

from __future__ import annotations

from pathlib import Path

import pytest
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from sfu_converter.config import SIBFUConfig
from sfu_converter.domain.formatting import (
    FormattingProfile,
    FormattingRule,
    RuleSeverity,
    RuleStatus,
)
from sfu_converter.registry import (
    ALL_RULES,
    COMMON_RULES,
    PROFILES,
    RULES_BY_ID,
    build_legacy_config,
    get_profile,
    get_rule,
    iter_profiles,
    iter_rules,
)
from sfu_converter.registry.loader import _alignment, rules_with_status

REPO_ROOT = Path(__file__).resolve().parents[1]


def assert_close(actual, expected) -> None:
    assert abs(actual - expected) < 1000


def test_every_rule_id_is_unique():
    ids = [rule.id for rule in ALL_RULES]
    assert len(ids) == len(set(ids))


def test_rule_id_naming_convention():
    for rule in ALL_RULES:
        parts = rule.id.split(".")
        assert len(parts) >= 3, f"Rule id should follow doc.section.element: {rule.id}"
        assert all(parts), f"Empty segment in rule id: {rule.id}"


def test_rules_by_id_is_complete():
    assert set(RULES_BY_ID) == {rule.id for rule in ALL_RULES}


def test_iter_helpers_match_collections():
    assert list(iter_rules()) == list(ALL_RULES)
    assert list(iter_profiles()) == list(PROFILES.values())


def test_get_rule_returns_matching_entry():
    rule = get_rule("common.text.font.name")
    assert isinstance(rule, FormattingRule)
    assert rule.parameters["font_name"] == "Times New Roman"


def test_get_rule_missing_raises():
    with pytest.raises(KeyError):
        get_rule("does.not.exist")


def test_get_profile_returns_profile():
    profile = get_profile("common")
    assert isinstance(profile, FormattingProfile)
    assert profile.rules == COMMON_RULES


def test_profiles_inherit_common_rules():
    for profile in PROFILES.values():
        for rule in COMMON_RULES:
            assert rule in profile.rules, (
                f"Profile {profile.name} missing common rule {rule.id}"
            )


def test_document_profiles_add_profile_specific_rules():
    for profile in PROFILES.values():
        if profile.name == "common":
            assert profile.rules == COMMON_RULES
        else:
            assert len(profile.rules) > len(COMMON_RULES)


def test_coursework_and_vkr_profiles_include_inherited_source_docs():
    coursework = get_profile("coursework")
    assert "docs/formatting requirements/project_designations.md" in coursework.source_docs

    vkr = get_profile("graduation_qualification_work")
    assert "docs/formatting requirements/graphic_and_demonstration_materials.md" in vkr.source_docs
    assert "docs/formatting requirements/project_designations.md" in vkr.source_docs


def test_profile_specific_title_page_rules_are_addressable():
    lab_rule = get_rule("lab_practical_project_reports.title_page.form_m")
    assert lab_rule.parameters["form"] == "appendix_m"
    assert "student" in lab_rule.parameters["required_metadata"]

    coursework_rule = get_rule("coursework.title_page.form_i")
    assert coursework_rule in get_profile("coursework").rules


def test_rules_with_status_filters_by_renderer():
    not_supported = rules_with_status(renderer=RuleStatus.NOT_SUPPORTED)
    assert all(rule.renderer_status is RuleStatus.NOT_SUPPORTED for rule in not_supported)

    implemented = rules_with_status(renderer=RuleStatus.IMPLEMENTED)
    assert any(rule.id == "common.page.numbering" for rule in implemented)

    validator_supported = rules_with_status(validator=RuleStatus.IMPLEMENTED)
    assert all(rule.validator_status is RuleStatus.IMPLEMENTED for rule in validator_supported)


def test_alignment_rejects_unknown_values():
    with pytest.raises(ValueError, match="Unknown alignment value"):
        _alignment("diagonal")


def test_required_severity_is_used_for_core_rules():
    font_size_rule = get_rule("common.text.font.size")
    assert font_size_rule.severity is RuleSeverity.REQUIRED


def test_common_profile_size_grew_with_registry_expansion():
    common_profile = get_profile("common")
    assert len(common_profile.rules) >= 80


def test_every_source_doc_lives_under_formatting_requirements_dir():
    formatting_dir = REPO_ROOT / "docs" / "formatting requirements"
    for rule in ALL_RULES:
        rule_doc = (REPO_ROOT / rule.source_doc).resolve()
        assert formatting_dir.resolve() in rule_doc.parents, (
            f"Rule {rule.id} source_doc must live under docs/formatting requirements/: {rule.source_doc}"
        )


def test_coursework_profile_contains_required_rules():
    coursework = get_profile("coursework")
    rule_ids = {rule.id for rule in coursework.rules}
    assert "coursework.frame.course_project_explanatory_note" in rule_ids
    assert "coursework.title_block.field_2_designation" in rule_ids
    assert "project_designations.code.format" in rule_ids


def test_graduation_qualification_work_includes_all_title_page_forms():
    vkr = get_profile("graduation_qualification_work")
    rule_ids = {rule.id for rule in vkr.rules}
    for letter in ("b", "v", "g", "d", "e", "zh"):
        assert f"graduation_qualification_work.title_page.form_{letter}" in rule_ids, (
            f"VKR profile missing form_{letter}"
        )


def test_practice_reports_form_k_supports_four_heading_variants():
    rule = get_rule("practice_reports.title_page.form_k.headings")
    assert "ОТЧЕТ ОБ УЧЕБНОЙ ПРАКТИКЕ" in rule.parameters["variants"]
    assert "ОТЧЕТ О ПРОИЗВОДСТВЕННОЙ ПРАКТИКЕ" in rule.parameters["variants"]
    assert "ОТЧЕТ О ПРЕДДИПЛОМНОЙ ПРАКТИКЕ" in rule.parameters["variants"]
    assert "ОТЧЕТ О ТЕХНОЛОГИЧЕСКОЙ ПРАКТИКЕ" in rule.parameters["variants"]


def test_project_designation_code_dictionary_is_complete():
    rule = get_rule("project_designations.code.dictionary")
    expected_codes = {
        "ПЗ", "РР", "ПМ", "И", "Д", "ВС", "ВП", "ТБ", "ТУ", "СБ", "ВО",
        "ТЧ", "ГЧ", "МЭ", "МЧ", "УЧ", "МК", "КТП", "ОК", "ВОБ", "ВМ",
        "С", "ЛС", "ТХ", "ГП", "ГТ", "АР", "АС", "АИ", "КЖ", "КМ",
        "КМД", "КД", "ВК", "ОВ", "ТМ", "ГСВ", "ГР", "НВ", "НК", "ТС",
        "АД", "ТР",
    }
    assert expected_codes <= set(rule.parameters["document_codes"])
    assert {"Э", "Г", "П", "К", "В", "Л", "Р", "Е", "С"} <= set(rule.parameters["scheme_type_codes"])
    assert {"1", "2", "3", "4", "5", "6", "7", "0"} <= set(rule.parameters["scheme_subtype_numbers"])


def test_legacy_config_dict_matches_sibfu_config_attributes():
    legacy = build_legacy_config()

    assert legacy["FONT_NAME"] == SIBFUConfig.FONT_NAME == "Times New Roman"
    assert legacy["FONT_SIZE"] == SIBFUConfig.FONT_SIZE == Pt(14)
    assert legacy["FONT_COLOR_RGB"] == SIBFUConfig.FONT_COLOR_RGB == (0, 0, 0)
    assert legacy["LINE_SPACING_NORMAL"] == SIBFUConfig.LINE_SPACING_NORMAL == 1.5
    assert legacy["ALIGNMENT"] == SIBFUConfig.ALIGNMENT == WD_ALIGN_PARAGRAPH.JUSTIFY

    assert_close(legacy["FIRST_LINE_INDENT"], Cm(1.25))
    assert_close(SIBFUConfig.FIRST_LINE_INDENT, Cm(1.25))


def test_legacy_config_margins_match_standard():
    margins = build_legacy_config()["MARGINS"]
    assert_close(margins["top"], Cm(2))
    assert_close(margins["bottom"], Cm(2))
    assert_close(margins["left"], Cm(3))
    assert_close(margins["right"], Cm(1))


def test_legacy_config_image_block_preserves_keys():
    image = build_legacy_config()["IMAGE"]
    assert set(image.keys()) >= {
        "line_spacing",
        "alignment",
        "width",
        "height",
        "dpi",
        "format",
        "max_width",
    }
    assert image["alignment"] == WD_ALIGN_PARAGRAPH.CENTER
    assert image["width"] is None
    assert image["height"] is None
    assert image["dpi"] == (96, 96)
    assert_close(image["max_width"], Cm(15))


def test_heading_blocks_round_trip_through_config():
    legacy = build_legacy_config()
    assert legacy["H1"]["align"] == WD_ALIGN_PARAGRAPH.LEFT
    assert legacy["H1"]["bold"] is True
    assert_close(legacy["H1"]["indent"], Cm(1.25))
    assert legacy["H2"]["align"] == WD_ALIGN_PARAGRAPH.LEFT
    assert legacy["H2"]["bold"] is True
    assert legacy["H3"]["bold"] is False


def test_list_item_block_round_trips_through_config():
    legacy = build_legacy_config()

    assert legacy["LIST_ITEM"]["align"] == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert legacy["LIST_ITEM"]["bold"] is False
    assert legacy["LIST_ITEM"]["line_spacing"] == 1.5
    assert_close(legacy["LIST_ITEM"]["indent"], Cm(1.25))
    assert SIBFUConfig.LIST_ITEM == legacy["LIST_ITEM"]


def test_page_numbering_and_structural_sections_round_trip_through_config():
    legacy = build_legacy_config()

    page_numbering = legacy["PAGE_NUMBERING"]
    assert page_numbering["position"] == "bottom_center"
    assert page_numbering["format"] == "arabic"
    assert page_numbering["skip_first_page"] is True
    assert page_numbering["font_name"] == SIBFUConfig.FONT_NAME
    assert page_numbering["font_size"] == Pt(14)

    structural = legacy["STRUCTURAL_SECTION"]
    assert structural["align"] == WD_ALIGN_PARAGRAPH.CENTER
    assert structural["bold"] is True
    assert_close(structural["indent"], Cm(0))
    assert structural["uppercase"] is True
    assert structural["page_break_before"] is True

    assert "ВВЕДЕНИЕ" in legacy["STRUCTURAL_HEADINGS"]
    assert "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ" in SIBFUConfig.STRUCTURAL_HEADINGS


def test_table_body_block_round_trips_through_config():
    legacy = build_legacy_config()
    table = legacy["TABLE"]

    assert table["font_size"] == Pt(12)
    assert table["header_font_size"] == Pt(12)
    assert table["header_bold"] is True
    assert table["line_spacing"] == 1.0
    assert table["header_repeat_on_pages"] is True
    assert table["cell_padding"] == Pt(6)
    assert SIBFUConfig.TABLE == table


def test_task_14_and_15_rules_are_marked_implemented():
    implemented_renderer = {
        "common.abbreviations.two_column_layout",
        "common.table.borders",
        "common.table.subheader",
        "common.table.no_period_in_header",
        "common.table.unit_label",
        "common.table.column_unit_suffix",
        "common.table.continuation_label",
        "common.table.numbering_row_replacement",
        "common.table.forbid_serial_column",
        "common.table.no_diagonal_split",
        "common.table.footnote",
        "common.table.italic_letters",
        "common.table.cell_padding",
        "common.table.body",
        "common.table.spacing_before",
        "common.table.spacing_after",
    }
    implemented_validator = implemented_renderer

    for rule_id in implemented_renderer:
        assert get_rule(rule_id).renderer_status is RuleStatus.IMPLEMENTED
    for rule_id in implemented_validator:
        assert get_rule(rule_id).validator_status is RuleStatus.IMPLEMENTED


def test_task_16_and_17_rules_are_marked_implemented():
    implemented_renderer = {
        "common.figure.section_numbering",
        "common.figure.appendix_numbering",
        "common.figure.placement_after_reference",
        "common.figure.explanatory_data",
        "common.figure.multi_sheet_label",
        "common.figure.image",
        "common.formula.body_indent",
        "common.formula.section_numbering",
        "common.formula.appendix_numbering",
        "common.formula.line_continuation",
        "common.formula.explanation_marker",
        "common.formula.repeated_symbol",
        "common.formula.consecutive_comma",
    }
    implemented_validator = implemented_renderer

    for rule_id in implemented_renderer:
        assert get_rule(rule_id).renderer_status is RuleStatus.IMPLEMENTED
    for rule_id in implemented_validator:
        assert get_rule(rule_id).validator_status is RuleStatus.IMPLEMENTED


def test_task_18_and_19_rules_are_marked_implemented():
    implemented = {
        "common.bibliography.gost_record",
        "common.bibliography.gost_abbreviations",
        "common.bibliography.grouping_method",
        "common.bibliography.russian_first",
        "common.reference.footnote",
    }

    for rule_id in implemented:
        assert get_rule(rule_id).renderer_status is RuleStatus.IMPLEMENTED
        assert get_rule(rule_id).validator_status is RuleStatus.IMPLEMENTED


def test_task_20_and_21_reference_rules_are_marked_implemented():
    implemented = {
        "common.reference.in_text_simple",
        "common.reference.in_text_pages",
        "common.reference.in_text_volume",
        "common.reference.in_text_group",
        "common.reference.cross_check",
        "common.reference.figure_table_formula",
        "common.appendix.in_text_reference",
    }

    for rule_id in implemented:
        assert get_rule(rule_id).renderer_status is RuleStatus.IMPLEMENTED
        assert get_rule(rule_id).validator_status is RuleStatus.IMPLEMENTED


def test_task_25_and_26_rules_are_marked_implemented():
    implemented = {
        "project_designations.title_block.letter_numeric_designation",
        "project_designations.code.dictionary",
        "project_designations.code.format",
        "common.style.abbreviation_introduction",
        "common.style.no_abbreviations_in_headings",
        "common.style.unit_consistency",
    }

    for rule_id in implemented:
        assert get_rule(rule_id).renderer_status is RuleStatus.IMPLEMENTED
        assert get_rule(rule_id).validator_status is RuleStatus.IMPLEMENTED
