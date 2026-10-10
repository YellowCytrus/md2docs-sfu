from __future__ import annotations

from collections.abc import Iterable

from sfu_converter.domain.ast_nodes import Document, HeadingLevel, HeadingNode, SourceSpan
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile


def run(document: Document, profile: FormattingProfile) -> list[Diagnostic]:
    """Validate heading text and H3/H4 structural quality rules."""

    rule_ids = {rule.id for rule in profile.rules}
    headings = tuple(_iter_headings(document.blocks))
    diagnostics: list[Diagnostic] = []

    if "common.heading.no_hyphenation" in rule_ids:
        diagnostics.extend(_hyphenation_diagnostics(headings))
    if "common.heading.two_sentence_separator" in rule_ids:
        diagnostics.extend(_two_sentence_diagnostics(headings))
    if "common.heading.point_requires_subpoints" in rule_ids:
        diagnostics.extend(_point_subpoint_diagnostics(headings, profile))

    return diagnostics


def _iter_headings(blocks: Iterable[object]) -> Iterable[HeadingNode]:
    for block in blocks:
        if isinstance(block, HeadingNode):
            yield block
            continue
        child_blocks = getattr(block, "blocks", None)
        if child_blocks is not None:
            yield from _iter_headings(child_blocks)


def _hyphenation_diagnostics(headings: Iterable[HeadingNode]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for heading in headings:
        if "\u00ad" not in heading.text and "-\n" not in heading.text and "-\r\n" not in heading.text:
            continue
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.HEADING_HYPHENATION,
                message="Heading must not contain soft hyphens or explicit word-break hyphenation",
                severity=Severity.ERROR,
                rule_id="common.heading.no_hyphenation",
                source=heading.source,
            )
        )
    return diagnostics


def _two_sentence_diagnostics(headings: Iterable[HeadingNode]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for heading in headings:
        text = " ".join(heading.text.strip().splitlines())
        first_period = text.find(".")
        if first_period < 0 or first_period == len(text) - 1:
            continue

        follows_single_space = (
            first_period + 2 < len(text)
            and text[first_period + 1] == " "
            and text[first_period + 2] != " "
        )
        second_sentence_has_final_period = text.endswith(".")
        if follows_single_space and not second_sentence_has_final_period:
            continue

        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.HEADING_TWO_SENTENCE,
                message=(
                    "Two-sentence heading must use one space after the first "
                    "period and must not end the second sentence with a period"
                ),
                severity=Severity.ERROR,
                rule_id="common.heading.two_sentence_separator",
                source=heading.source,
            )
        )
    return diagnostics


def _point_subpoint_diagnostics(
    headings: tuple[HeadingNode, ...],
    profile: FormattingProfile,
) -> list[Diagnostic]:
    min_subpoints = _min_subpoints(profile)
    diagnostics: list[Diagnostic] = []
    for group in _h3_groups(headings):
        h3_count = sum(1 for heading in group if heading.level is HeadingLevel.H3)
        has_h4 = any(heading.level is HeadingLevel.H4 for heading in group)
        if h3_count <= 1 or not has_h4:
            continue
        diagnostics.extend(_single_subpoint_diagnostics(group, min_subpoints))
    return diagnostics


def _h3_groups(headings: tuple[HeadingNode, ...]) -> Iterable[tuple[HeadingNode, ...]]:
    current: list[HeadingNode] = []
    for heading in headings:
        if heading.level in {HeadingLevel.H1, HeadingLevel.H2}:
            if current:
                yield tuple(current)
                current = []
            continue
        if heading.level in {HeadingLevel.H3, HeadingLevel.H4}:
            current.append(heading)
    if current:
        yield tuple(current)


def _single_subpoint_diagnostics(
    group: tuple[HeadingNode, ...],
    min_subpoints: int,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for index, heading in enumerate(group):
        if heading.level is not HeadingLevel.H3:
            continue
        direct_h4_count = 0
        for child in group[index + 1 :]:
            if child.level is HeadingLevel.H3:
                break
            if child.level is HeadingLevel.H4:
                direct_h4_count += 1
        if direct_h4_count == 0 or direct_h4_count >= min_subpoints:
            continue
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.HEADING_POINT_REQUIRES_SUBPOINTS,
                message=(
                    f"Point heading has {direct_h4_count} subpoint, "
                    f"expected at least {min_subpoints}"
                ),
                severity=Severity.ERROR,
                rule_id="common.heading.point_requires_subpoints",
                source=_source(heading),
                data={"subpoint_count": direct_h4_count},
            )
        )
    return diagnostics


def _min_subpoints(profile: FormattingProfile) -> int:
    for rule in profile.rules:
        if rule.id == "common.heading.point_requires_subpoints":
            return int(rule.parameters.get("min_subpoints", 2))
    return 2


def _source(heading: HeadingNode) -> SourceSpan | None:
    return heading.source
