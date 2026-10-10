"""Coverage matrix tests.

# rule: common.registry.coverage_matrix
"""

from __future__ import annotations

import json

from sfu_converter.domain.formatting import RuleStatus
from sfu_converter.registry import ALL_RULES
from sfu_converter.registry.coverage import build_rows, render_json, render_markdown


def test_coverage_rows_are_deterministic_and_complete():
    first = build_rows()
    second = build_rows()

    assert first == second
    assert [row.rule_id for row in first] == sorted(rule.id for rule in ALL_RULES)
    assert len({row.rule_id for row in first}) == len(ALL_RULES)


def test_coverage_rows_include_profile_membership_and_statuses():
    rows = {row.rule_id: row for row in build_rows()}

    common_heading = rows["common.heading.h1"]
    assert "common" in common_heading.profiles
    assert "coursework" in common_heading.profiles
    assert common_heading.renderer_status == RuleStatus.IMPLEMENTED.value
    assert common_heading.validator_status == RuleStatus.IMPLEMENTED.value
    assert common_heading.parser_support is True

    coursework_rule = rows["coursework.title_page.form_i"]
    assert coursework_rule.profiles == ("coursework",)


def test_coverage_renderers_are_stable_and_include_source_links():
    rows = build_rows()
    markdown = render_markdown(rows)
    payload = json.loads(render_json(rows))

    assert markdown.startswith("# SFU Standard Coverage Matrix\n")
    assert "| Rule ID | Profiles | Source | Severity | Parser | Renderer | Validator | Tests |" in markdown
    assert "common.heading.h1" in markdown
    assert payload["rows"][0]["ruleId"] == rows[0].rule_id
    assert payload["rows"][0]["sourceDoc"] == rows[0].source_doc
