"""Helpers for surfacing renderer/validator coverage gaps in a profile.

Implements Task 03 of ``docs/tasks/03-emit-unsupported-rule-diagnostics.md``:
agents and operators must be able to discover, before any conversion or
validation runs, which formatting rules from the chosen profile will be
silently skipped because they are flagged ``RuleStatus.NOT_SUPPORTED``.
"""

from __future__ import annotations

from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile, FormattingRule, RuleStatus

UNSUPPORTED_RULE_MESSAGE = "Rule {rule_id} is not supported by the {target}"
"""Message template for ``FORMAT_RULE_NOT_SUPPORTED`` diagnostics."""

_VALID_TARGETS = frozenset({"renderer", "validator"})


def unsupported_renderer_rules(profile: FormattingProfile) -> tuple[FormattingRule, ...]:
    """Return rules in ``profile`` whose renderer status is NOT_SUPPORTED."""

    return tuple(rule for rule in profile.rules if rule.renderer_status is RuleStatus.NOT_SUPPORTED)


def unsupported_validator_rules(profile: FormattingProfile) -> tuple[FormattingRule, ...]:
    """Return rules in ``profile`` whose validator status is NOT_SUPPORTED."""

    return tuple(rule for rule in profile.rules if rule.validator_status is RuleStatus.NOT_SUPPORTED)


def support_diagnostics(profile: FormattingProfile, *, target: str) -> list[Diagnostic]:
    """Return one ``FORMAT_RULE_NOT_SUPPORTED`` diagnostic per uncovered rule."""

    if target not in _VALID_TARGETS:
        raise ValueError(f"Unsupported target: {target!r}")

    rules = unsupported_renderer_rules(profile) if target == "renderer" else unsupported_validator_rules(profile)
    return [_diagnostic_for_rule(rule, target=target) for rule in rules]


def _diagnostic_for_rule(rule: FormattingRule, *, target: str) -> Diagnostic:
    return Diagnostic(
        code=DiagnosticCodes.FORMAT_RULE_NOT_SUPPORTED,
        message=UNSUPPORTED_RULE_MESSAGE.format(rule_id=rule.id, target=target),
        severity=Severity.WARNING,
        rule_id=rule.id,
        target=target,
        data={
            "source_doc": rule.source_doc,
            "source_section": rule.source_section,
        },
    )
