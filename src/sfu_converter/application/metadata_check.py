from __future__ import annotations

from collections.abc import Mapping

from sfu_converter.domain.ast_nodes import Document
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile, FormattingRule


def run(
    document: Document,
    profile: FormattingProfile,
    *,
    severity: Severity = Severity.WARNING,
) -> list[Diagnostic]:
    metadata = document.metadata
    diagnostics: list[Diagnostic] = []

    for rule in profile.rules:
        if rule.id.endswith(".metadata.required"):
            diagnostics.extend(_diagnostics_for_rule(metadata, profile, rule, severity=severity))

    selected_rule = _selected_title_page_rule(profile)
    if selected_rule is not None:
        required = _selected_title_page_required_metadata(profile, selected_rule)
        diagnostics.extend(
            _diagnostics_for_required(
                metadata,
                profile,
                selected_rule,
                required,
                severity=severity,
            )
        )

    return _deduplicate(diagnostics)


def _diagnostics_for_rule(
    metadata: Mapping[str, str],
    profile: FormattingProfile,
    rule: FormattingRule,
    *,
    severity: Severity,
) -> list[Diagnostic]:
    required = tuple(rule.parameters.get("required_metadata", ()))
    return _diagnostics_for_required(metadata, profile, rule, required, severity=severity)


def _diagnostics_for_required(
    metadata: Mapping[str, str],
    profile: FormattingProfile,
    rule: FormattingRule,
    required: tuple[str, ...],
    *,
    severity: Severity,
) -> list[Diagnostic]:
    missing = sorted(field for field in required if not str(metadata.get(field, "")).strip())
    if not missing:
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.TXT_MISSING_METADATA,
            message=(
                f"Profile '{profile.name}' missing required metadata for "
                f"{rule.id}: {', '.join(missing)}"
            ),
            severity=severity,
            rule_id=rule.id,
            data={
                "profile": profile.name,
                "missing": missing,
                "ruleId": rule.id,
            },
        )
    ]


def _selected_title_page_rule(profile: FormattingProfile) -> FormattingRule | None:
    for rule in profile.rules:
        if ".title_page.form_" not in rule.id:
            continue
        if ".required_metadata" in rule.id:
            continue
        if "form" in rule.parameters:
            return rule
    return None


def _selected_title_page_required_metadata(
    profile: FormattingProfile,
    selected_rule: FormattingRule,
) -> tuple[str, ...]:
    fields: list[str] = list(selected_rule.parameters.get("required_metadata", ()))
    prefix = f"{selected_rule.id}."
    for rule in profile.rules:
        if not rule.id.startswith(prefix):
            continue
        for field in rule.parameters.get("required_metadata", ()):
            if field not in fields:
                fields.append(field)
    return tuple(fields)


def _deduplicate(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[tuple[str, str | None, tuple[str, ...]]] = set()
    result: list[Diagnostic] = []
    for diagnostic in diagnostics:
        missing = tuple(diagnostic.data.get("missing", ())) if diagnostic.data else ()
        key = (diagnostic.code, diagnostic.rule_id, missing)
        if key in seen:
            continue
        seen.add(key)
        result.append(diagnostic)
    return result
