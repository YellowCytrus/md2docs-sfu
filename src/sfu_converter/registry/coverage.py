from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from sfu_converter.domain.formatting import FormattingRule
from sfu_converter.parser.syntax_spec import get_syntax_spec
from sfu_converter.registry.loader import iter_profiles, iter_rules

_RULE_MARKER_RE = re.compile(r"^\s*#\s*rule:\s*(?P<rule_id>[A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class CoverageRow:
    rule_id: str
    profiles: tuple[str, ...]
    source_doc: str
    source_section: str
    severity: str
    parser_support: bool
    renderer_status: str
    validator_status: str
    test_modules: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "ruleId": self.rule_id,
            "profiles": list(self.profiles),
            "sourceDoc": self.source_doc,
            "sourceSection": self.source_section,
            "severity": self.severity,
            "parserSupport": self.parser_support,
            "rendererStatus": self.renderer_status,
            "validatorStatus": self.validator_status,
            "testModules": list(self.test_modules),
        }


def build_rows(*, repo_root: Path | None = None, tests_dir: Path | None = None) -> list[CoverageRow]:
    root = repo_root or _REPO_ROOT
    test_markers = _collect_test_markers(tests_dir or root / "tests", root)
    profiles_by_rule = _profiles_by_rule()
    rows = [
        _row_for_rule(rule, profiles_by_rule=profiles_by_rule, test_markers=test_markers)
        for rule in sorted(iter_rules(), key=lambda item: item.id)
    ]
    return rows


def render_markdown(rows: list[CoverageRow]) -> str:
    lines = [
        "# SFU Standard Coverage Matrix",
        "",
        "Generated from `src/sfu_converter/registry` rule metadata.",
        "",
        "| Rule ID | Profiles | Source | Severity | Parser | Renderer | Validator | Tests |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        source = f"{_escape(row.source_section)}<br>`{_escape(row.source_doc)}`"
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{_escape(row.rule_id)}`",
                    _escape(", ".join(row.profiles)),
                    source,
                    _escape(row.severity),
                    "yes" if row.parser_support else "no",
                    _escape(row.renderer_status),
                    _escape(row.validator_status),
                    _escape(", ".join(row.test_modules) if row.test_modules else "-"),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_json(rows: list[CoverageRow]) -> str:
    payload = {"rows": [row.to_json() for row in rows]}
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parser_support_for_rule(rule: FormattingRule) -> bool:
    features = _parser_features()
    parts = rule.id.split(".")
    candidates = set(parts)
    if len(parts) > 1:
        candidates.add(parts[1])
    aliases = {
        "abbreviations": "paragraph",
        "appendix": "appendix",
        "bibliography": "source",
        "figure": "figure",
        "formula": "formula",
        "heading": "heading",
        "list": "list",
        "metadata": "metadata",
        "page": "page_break",
        "reference": "reference",
        "structural": "heading",
        "style": "paragraph",
        "table": "table",
        "text": "paragraph",
        "title_page": "title_page",
        "toc": "table_of_contents",
    }
    candidates.update(aliases.get(part, part) for part in parts)
    return bool(candidates & features)


def _row_for_rule(
    rule: FormattingRule,
    *,
    profiles_by_rule: dict[str, tuple[str, ...]],
    test_markers: dict[str, tuple[str, ...]],
) -> CoverageRow:
    return CoverageRow(
        rule_id=rule.id,
        profiles=profiles_by_rule.get(rule.id, ()),
        source_doc=rule.source_doc,
        source_section=rule.source_section,
        severity=rule.severity.value,
        parser_support=parser_support_for_rule(rule),
        renderer_status=rule.renderer_status.value,
        validator_status=rule.validator_status.value,
        test_modules=test_markers.get(rule.id, ()),
    )


def _profiles_by_rule() -> dict[str, tuple[str, ...]]:
    memberships: dict[str, list[str]] = {}
    for profile in iter_profiles():
        for rule in profile.rules:
            memberships.setdefault(rule.id, []).append(profile.name)
    return {rule_id: tuple(sorted(names)) for rule_id, names in memberships.items()}


def _collect_test_markers(tests_dir: Path, repo_root: Path) -> dict[str, tuple[str, ...]]:
    found: dict[str, set[str]] = {}
    if not tests_dir.exists():
        return {}
    for path in sorted(tests_dir.rglob("test*.py")):
        marker_text = _module_docstring(path)
        if not marker_text:
            continue
        rel = path.relative_to(repo_root).as_posix()
        for match in _RULE_MARKER_RE.finditer(marker_text):
            found.setdefault(match.group("rule_id"), set()).add(rel)
    return {rule_id: tuple(sorted(paths)) for rule_id, paths in sorted(found.items())}


def _module_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return ""
    return ast.get_docstring(tree) or ""


def _parser_features() -> set[str]:
    features: set[str] = set()
    for version in (1, 2):
        for block in get_syntax_spec(version)["blocks"]:
            features.add(str(block["name"]))
            features.add(str(block["node"]).removesuffix("Node").lower())
    return features


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|")
