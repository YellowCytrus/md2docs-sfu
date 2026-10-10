"""Tests for infrastructure.numbering — NumberingContext and friends."""

import pytest

from sfu_converter.domain.ast_nodes import HeadingLevel
from sfu_converter.domain.formatting import FormattingProfile, FormattingRule, RuleSeverity, RuleStatus
from sfu_converter.infrastructure.numbering import (
    NumberingContext,
    NumberingMode,
    NumberingModes,
    build_numbering_context,
)


def _ctx(formula=NumberingMode.GLOBAL, table=NumberingMode.GLOBAL, figure=NumberingMode.GLOBAL):
    return NumberingContext(NumberingModes(formula=formula, table=table, figure=figure))


class TestGlobalNumbering:
    def test_formula_global_sequential(self):
        ctx = _ctx()
        assert ctx.next_formula_number() == "1"
        assert ctx.next_formula_number() == "2"
        assert ctx.next_formula_number() == "3"

    def test_table_global_sequential(self):
        ctx = _ctx()
        assert ctx.next_table_number() == "1"
        assert ctx.next_table_number() == "2"

    def test_figure_global_sequential(self):
        ctx = _ctx()
        assert ctx.next_figure_number() == "1"
        assert ctx.next_figure_number() == "2"

    def test_global_ignores_section_changes(self):
        ctx = _ctx()
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "1"
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "2"


class TestSectionNumbering:
    def test_formula_section_numbering(self):
        ctx = _ctx(formula=NumberingMode.SECTION)
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "1.1"
        assert ctx.next_formula_number() == "1.2"

        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "2.1"

        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "3.1"

    def test_table_section_numbering(self):
        ctx = _ctx(table=NumberingMode.SECTION)
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_table_number() == "1.1"
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_table_number() == "2.1"

    def test_figure_section_numbering(self):
        ctx = _ctx(figure=NumberingMode.SECTION)
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_figure_number() == "1.1"
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_figure_number() == "2.1"

    def test_section_resets_counters_on_h1(self):
        ctx = _ctx(formula=NumberingMode.SECTION, table=NumberingMode.SECTION)
        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "1.1"
        assert ctx.next_table_number() == "1.1"

        ctx.next_section_number(HeadingLevel.H2)
        assert ctx.next_formula_number() == "1.1"

        ctx.next_section_number(HeadingLevel.H1)
        assert ctx.next_formula_number() == "2.1"
        assert ctx.next_table_number() == "2.1"


class TestAppendixNumbering:
    def test_formula_in_appendix(self):
        ctx = _ctx()
        ctx.enter_appendix("А")
        assert ctx.next_formula_number() == "А.1"
        assert ctx.next_formula_number() == "А.2"

    def test_table_in_appendix(self):
        ctx = _ctx()
        ctx.enter_appendix("А")
        assert ctx.next_table_number() == "А.1"

    def test_figure_in_appendix(self):
        ctx = _ctx()
        ctx.enter_appendix("Б")
        assert ctx.next_figure_number() == "Б.1"

    def test_heading_in_appendix(self):
        ctx = _ctx()
        ctx.enter_appendix("А")
        assert ctx.next_section_number(HeadingLevel.H1) == "А.1"
        assert ctx.next_section_number(HeadingLevel.H2) == "А.1.1"
        assert ctx.next_section_number(HeadingLevel.H1) == "А.2"

    def test_counters_reset_on_new_appendix(self):
        ctx = _ctx()
        ctx.enter_appendix("А")
        assert ctx.next_formula_number() == "А.1"
        assert ctx.next_table_number() == "А.1"
        ctx.leave_appendix()

        ctx.enter_appendix("Б")
        assert ctx.next_formula_number() == "Б.1"
        assert ctx.next_table_number() == "Б.1"

    def test_nested_appendix_restores_outer(self):
        ctx = _ctx()
        ctx.enter_appendix("А")
        assert ctx.next_formula_number() == "А.1"
        ctx.enter_appendix("Б")
        assert ctx.next_formula_number() == "Б.1"
        ctx.leave_appendix()
        assert ctx.next_formula_number() == "А.2"

    def test_appendix_letter_property(self):
        ctx = _ctx()
        assert ctx.appendix_letter is None
        ctx.enter_appendix("В")
        assert ctx.appendix_letter == "В"
        ctx.leave_appendix()
        assert ctx.appendix_letter is None

    def test_body_counters_survive_appendix(self):
        ctx = _ctx()
        assert ctx.next_formula_number() == "1"
        ctx.enter_appendix("А")
        assert ctx.next_formula_number() == "А.1"
        ctx.leave_appendix()
        assert ctx.next_formula_number() == "2"


class TestSectionHeadingNumbers:
    def test_hierarchical_numbering(self):
        ctx = _ctx()
        assert ctx.next_section_number(HeadingLevel.H1) == "1"
        assert ctx.next_section_number(HeadingLevel.H2) == "1.1"
        assert ctx.next_section_number(HeadingLevel.H2) == "1.2"
        assert ctx.next_section_number(HeadingLevel.H3) == "1.2.1"
        assert ctx.next_section_number(HeadingLevel.H1) == "2"
        assert ctx.next_section_number(HeadingLevel.H2) == "2.1"

    def test_h4_numbering(self):
        ctx = _ctx()
        assert ctx.next_section_number(HeadingLevel.H1) == "1"
        assert ctx.next_section_number(HeadingLevel.H2) == "1.1"
        assert ctx.next_section_number(HeadingLevel.H3) == "1.1.1"
        assert ctx.next_section_number(HeadingLevel.H4) == "1.1.1.1"

    def test_invalid_level_raises(self):
        ctx = _ctx()
        with pytest.raises(ValueError, match="Unsupported heading level"):
            ctx.next_section_number(5)


class TestBuildNumberingContext:
    def test_no_profile_returns_global(self):
        ctx = build_numbering_context(None)
        assert ctx.modes.formula is NumberingMode.GLOBAL
        assert ctx.modes.table is NumberingMode.GLOBAL
        assert ctx.modes.figure is NumberingMode.GLOBAL

    def test_common_profile_stays_global(self):
        profile = FormattingProfile(
            name="common",
            display_name="Common",
            source_docs=("standard",),
            rules=(
                FormattingRule(
                    id="common.formula.section_numbering",
                    source_doc="common.md",
                    source_section="Formulas",
                    severity=RuleSeverity.RECOMMENDED,
                    parameters={"default_enabled": False},
                    renderer_status=RuleStatus.IMPLEMENTED,
                ),
            ),
        )
        ctx = build_numbering_context(profile)
        assert ctx.modes.formula is NumberingMode.GLOBAL

    def test_vkr_profile_enables_section(self):
        profile = FormattingProfile(
            name="vkr",
            display_name="VKR",
            source_docs=("standard",),
            rules=(
                FormattingRule(
                    id="common.formula.section_numbering",
                    source_doc="common.md",
                    source_section="Formulas",
                    severity=RuleSeverity.RECOMMENDED,
                    parameters={"default_enabled": False},
                    renderer_status=RuleStatus.IMPLEMENTED,
                ),
                FormattingRule(
                    id="graduation_qualification_work.formula.section_numbering",
                    source_doc="vkr.md",
                    source_section="Formulas",
                    severity=RuleSeverity.REQUIRED,
                    parameters={"default_enabled": True},
                    renderer_status=RuleStatus.IMPLEMENTED,
                ),
            ),
        )
        ctx = build_numbering_context(profile)
        assert ctx.modes.formula is NumberingMode.SECTION

    def test_not_implemented_stays_global(self):
        profile = FormattingProfile(
            name="test",
            display_name="Test",
            source_docs=("standard",),
            rules=(
                FormattingRule(
                    id="test.formula.section_numbering",
                    source_doc="test.md",
                    source_section="Formulas",
                    severity=RuleSeverity.REQUIRED,
                    parameters={"default_enabled": True},
                    renderer_status=RuleStatus.NOT_SUPPORTED,
                ),
            ),
        )
        ctx = build_numbering_context(profile)
        assert ctx.modes.formula is NumberingMode.GLOBAL
