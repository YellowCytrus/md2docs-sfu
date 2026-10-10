from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity


class RuleSeverity(Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    ADVISORY = "advisory"


class RuleStatus(Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    NOT_SUPPORTED = "not_supported"


@dataclass(frozen=True)
class FormattingRule:
    """A single formatting rule linked to the SFU standard."""

    id: str
    source_doc: str
    source_section: str
    severity: RuleSeverity
    parameters: Mapping[str, Any] = field(default_factory=dict)
    renderer_status: RuleStatus = RuleStatus.NOT_SUPPORTED
    validator_status: RuleStatus = RuleStatus.NOT_SUPPORTED
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.parameters, MappingProxyType):
            object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True)
class FormattingProfile:
    """A collection of rules for a specific document type."""

    name: str
    display_name: str
    source_docs: tuple[str, ...]
    rules: tuple[FormattingRule, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_docs", tuple(self.source_docs))
        object.__setattr__(self, "rules", tuple(self.rules))


def unsupported_rule_diagnostics(profile: FormattingProfile, *, component: str) -> list[Diagnostic]:
    """Return warnings for profile rules not supported by a pipeline component.

    Thin wrapper preserved for backwards compatibility. ``component`` matches
    the ``target`` argument of :func:`sfu_converter.application.profile_support.support_diagnostics`,
    which is the canonical entry point introduced in Task 03.
    """

    from sfu_converter.application.profile_support import support_diagnostics

    if component not in {"renderer", "validator"}:
        raise ValueError(f"Unsupported rule support component: {component!r}")

    return support_diagnostics(profile, target=component)
