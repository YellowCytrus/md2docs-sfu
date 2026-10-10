"""Formatting rule registry.

Canonical source of truth for all formatting constants. Every rule is traceable
to a specific section in ``docs/formatting requirements/``.
"""

from sfu_converter.registry.loader import (
    build_legacy_config,
    get_profile,
    get_rule,
    iter_profiles,
    iter_rules,
)
from sfu_converter.registry.profiles import PROFILES
from sfu_converter.registry.rules import ALL_RULES, COMMON_RULES, RULES_BY_ID

__all__ = [
    "ALL_RULES",
    "COMMON_RULES",
    "PROFILES",
    "RULES_BY_ID",
    "build_legacy_config",
    "get_profile",
    "get_rule",
    "iter_profiles",
    "iter_rules",
]
