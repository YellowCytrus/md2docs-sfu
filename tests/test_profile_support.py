"""Tests for ``sfu_converter.application.profile_support``.

Covers the ``FORMAT_RULE_NOT_SUPPORTED`` enumeration emitted by Task 03.
"""

from __future__ import annotations

import pytest

from sfu_converter.application.profile_support import (
    UNSUPPORTED_RULE_MESSAGE,
    support_diagnostics,
    unsupported_renderer_rules,
    unsupported_validator_rules,
)
from sfu_converter.domain.diagnostics import DiagnosticCodes, Severity
from sfu_converter.domain.formatting import (
    FormattingProfile,
    FormattingRule,
    RuleSeverity,
    RuleStatus,
)
from sfu_converter.infrastructure.docx_validator import diagnostic_to_json
from sfu_converter.registry import get_profile


# Frozen fixture: rule IDs whose ``validator_status`` is NOT_SUPPORTED in the
# baseline ``common`` profile. Encoded explicitly so a regression that adds or
# silently drops a rule status fails this test instead of going unnoticed.
COMMON_VALIDATOR_UNSUPPORTED_IDS: tuple[str, ...] = (
    "common.figure.spacing_before",
    "common.figure.spacing_after",
    "common.formula.spacing_before",
    "common.formula.spacing_after",
    "common.formula.cross_reference",
    "common.table.section_numbering",
    "common.table.appendix_numbering",
    "common.referat.template",
    "common.referat.keywords_uppercase",
)


def _synthetic_profile(*, renderer: RuleStatus, validator: RuleStatus) -> FormattingProfile:
    rule = FormattingRule(
        id="synthetic.unit.rule",
        source_doc="docs/formatting requirements/common.md",
        source_section="Synthetic Section",
        severity=RuleSeverity.REQUIRED,
        renderer_status=renderer,
        validator_status=validator,
    )
    return FormattingProfile(
        name="synthetic",
        display_name="Synthetic",
        source_docs=("docs/formatting requirements/common.md",),
        rules=(rule,),
    )


def test_support_diagnostics_rejects_unknown_target():
    profile = _synthetic_profile(renderer=RuleStatus.IMPLEMENTED, validator=RuleStatus.IMPLEMENTED)
    with pytest.raises(ValueError):
        support_diagnostics(profile, target="parser")


def test_unsupported_renderer_rules_filters_by_renderer_status():
    profile = _synthetic_profile(renderer=RuleStatus.NOT_SUPPORTED, validator=RuleStatus.IMPLEMENTED)

    rules = unsupported_renderer_rules(profile)

    assert [rule.id for rule in rules] == ["synthetic.unit.rule"]
    assert unsupported_validator_rules(profile) == ()


def test_unsupported_validator_rules_filters_by_validator_status():
    profile = _synthetic_profile(renderer=RuleStatus.IMPLEMENTED, validator=RuleStatus.NOT_SUPPORTED)

    rules = unsupported_validator_rules(profile)

    assert [rule.id for rule in rules] == ["synthetic.unit.rule"]
    assert unsupported_renderer_rules(profile) == ()


def test_support_diagnostics_emits_one_warning_per_unsupported_rule():
    profile = _synthetic_profile(renderer=RuleStatus.NOT_SUPPORTED, validator=RuleStatus.IMPLEMENTED)

    diagnostics = support_diagnostics(profile, target="renderer")

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == DiagnosticCodes.FORMAT_RULE_NOT_SUPPORTED
    assert diagnostic.severity is Severity.WARNING
    assert diagnostic.rule_id == "synthetic.unit.rule"
    assert diagnostic.target == "renderer"
    assert diagnostic.message == UNSUPPORTED_RULE_MESSAGE.format(
        rule_id="synthetic.unit.rule",
        target="renderer",
    )
    assert diagnostic.data == {
        "source_doc": "docs/formatting requirements/common.md",
        "source_section": "Synthetic Section",
    }


def test_support_diagnostics_skips_implemented_rules():
    profile = _synthetic_profile(renderer=RuleStatus.IMPLEMENTED, validator=RuleStatus.IMPLEMENTED)

    assert support_diagnostics(profile, target="renderer") == []
    assert support_diagnostics(profile, target="validator") == []


def test_support_diagnostics_for_common_profile_matches_frozen_fixture():
    diagnostics = support_diagnostics(get_profile("common"), target="validator")

    assert tuple(diag.rule_id for diag in diagnostics) == COMMON_VALIDATOR_UNSUPPORTED_IDS
    assert all(diag.target == "validator" for diag in diagnostics)


def test_support_diagnostics_for_coursework_includes_known_unsupported_rules():
    diagnostics = support_diagnostics(get_profile("coursework"), target="renderer")
    rule_ids = {diag.rule_id for diag in diagnostics}

    assert "coursework.frame.course_project_explanatory_note" not in rule_ids
    assert "coursework.title_block.field_2_designation" in rule_ids


def test_diagnostic_round_trips_target_and_source_data():
    diagnostic = support_diagnostics(
        _synthetic_profile(renderer=RuleStatus.NOT_SUPPORTED, validator=RuleStatus.IMPLEMENTED),
        target="renderer",
    )[0]

    payload = diagnostic_to_json(diagnostic)

    assert payload["code"] == DiagnosticCodes.FORMAT_RULE_NOT_SUPPORTED
    assert payload["target"] == "renderer"
    assert payload["data"] == {
        "source_doc": "docs/formatting requirements/common.md",
        "source_section": "Synthetic Section",
    }
