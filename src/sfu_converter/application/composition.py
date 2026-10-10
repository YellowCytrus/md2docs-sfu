"""Structural document composition validation (§6.1).

Checks whether a parsed :class:`Document` carries the structural elements its
profile requires (title page, main part, mandatory sections) and whether the
structural sections appear in the canonical §6.1 order::

    TITLE_PAGE -> ASSIGNMENT_A -> REFERAT -> ANNOTATION -> CONTENTS ->
    INTRODUCTION -> MAIN_PART -> CONCLUSION -> ABBREVIATIONS -> SOURCES ->
    APPENDIX

Diagnostics are non-blocking warnings; the renderer still produces a DOCX even
when composition is invalid.
"""

from __future__ import annotations

from dataclasses import dataclass

from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    Document,
    HeadingNode,
    StructuralSectionNode,
    StructuralSectionType,
    TitlePageNode,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile

# Canonical order of structural sections per §6.1. Synthetic slots (title page,
# assignment, main part) are positioned by the surrounding sections rather than
# by a StructuralSectionType, so only true sections are indexed here.
_CANONICAL_ORDER: tuple[StructuralSectionType, ...] = (
    StructuralSectionType.ABSTRACT,
    StructuralSectionType.ANNOTATION,
    StructuralSectionType.CONTENTS,
    StructuralSectionType.INTRODUCTION,
    StructuralSectionType.CONCLUSION,
    StructuralSectionType.ABBREVIATIONS,
    StructuralSectionType.SOURCES,
    StructuralSectionType.APPENDIX,
)
_ORDER_INDEX = {section: i for i, section in enumerate(_CANONICAL_ORDER)}


@dataclass(frozen=True)
class CompositionSpec:
    """Per-profile structural requirements derived from §6.1 + registry rules."""

    title_page_rule_id: str | None
    structure_rule_id: str | None
    required_sections: tuple[StructuralSectionType, ...]
    requires_title_page: bool
    requires_main_part: bool


_DEFAULT_SPEC = CompositionSpec(
    title_page_rule_id=None,
    structure_rule_id=None,
    required_sections=(),
    requires_title_page=False,
    requires_main_part=False,
)

_SPECS: dict[str, CompositionSpec] = {
    "lab_practical_project_reports": CompositionSpec(
        title_page_rule_id="lab_practical_project_reports.title_page.form_m",
        structure_rule_id="lab_practical_project_reports.structure.required_sections",
        required_sections=(),
        requires_title_page=True,
        requires_main_part=True,
    ),
    "practice_reports": CompositionSpec(
        title_page_rule_id="practice_reports.title_page.form_k",
        structure_rule_id="practice_reports.structure.required_sections",
        required_sections=(),
        requires_title_page=True,
        requires_main_part=True,
    ),
    "research_reports": CompositionSpec(
        title_page_rule_id="research_reports.title_page.form_l",
        structure_rule_id="research_reports.structure.required_sections",
        required_sections=(
            StructuralSectionType.INTRODUCTION,
            StructuralSectionType.CONCLUSION,
            StructuralSectionType.SOURCES,
        ),
        requires_title_page=True,
        requires_main_part=True,
    ),
    "small_written_works": CompositionSpec(
        title_page_rule_id="small_written_works.title_page.form_n",
        structure_rule_id="small_written_works.structure.required_sections",
        required_sections=(),
        requires_title_page=True,
        requires_main_part=True,
    ),
    "coursework": CompositionSpec(
        title_page_rule_id="coursework.title_page.form_i",
        structure_rule_id="coursework.structure.required_sections",
        required_sections=(),
        requires_title_page=True,
        requires_main_part=True,
    ),
    "graduation_qualification_work": CompositionSpec(
        title_page_rule_id="graduation_qualification_work.title_page.form_b",
        structure_rule_id="graduation_qualification_work.structure.assignment_after_title",
        required_sections=(
            StructuralSectionType.ABSTRACT,
            StructuralSectionType.INTRODUCTION,
            StructuralSectionType.CONCLUSION,
            StructuralSectionType.SOURCES,
        ),
        requires_title_page=True,
        requires_main_part=True,
    ),
}


def spec_for(profile: FormattingProfile) -> CompositionSpec:
    return _SPECS.get(profile.name, _DEFAULT_SPEC)


@dataclass(frozen=True)
class _Occurrence:
    section_type: StructuralSectionType
    node: StructuralSectionNode | AppendixNode
    position: int


def validate(document: Document, profile: FormattingProfile) -> list[Diagnostic]:
    """Return composition diagnostics for ``document`` under ``profile``."""

    spec = spec_for(profile)
    diagnostics: list[Diagnostic] = []

    diagnostics.extend(_check_title_page(document, spec))
    diagnostics.extend(_check_main_part(document, spec))

    occurrences = _structural_occurrences(document)
    first_by_type = _first_by_type(occurrences)

    diagnostics.extend(_check_required_sections(spec, first_by_type))
    diagnostics.extend(_check_duplicates(occurrences))
    diagnostics.extend(_check_ordering(first_by_type))

    return diagnostics


def _check_title_page(document: Document, spec: CompositionSpec) -> list[Diagnostic]:
    if not spec.requires_title_page:
        return []
    if any(isinstance(block, TitlePageNode) for block in document.blocks):
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.STRUCTURE_TITLE_PAGE_MISSING,
            message="Document is missing a title page",
            severity=Severity.WARNING,
            rule_id=spec.title_page_rule_id,
        )
    ]


def _check_main_part(document: Document, spec: CompositionSpec) -> list[Diagnostic]:
    if not spec.requires_main_part:
        return []
    if _has_main_part(document):
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.STRUCTURE_MAIN_PART_MISSING,
            message="Document is missing a main part (no body headings)",
            severity=Severity.WARNING,
            rule_id=spec.structure_rule_id,
        )
    ]


def _has_main_part(document: Document) -> bool:
    blocks = document.blocks
    intro_pos = _first_section_position(blocks, StructuralSectionType.INTRODUCTION)
    if intro_pos is None:
        return any(isinstance(block, HeadingNode) for block in blocks)

    end_pos = len(blocks)
    for closing in (StructuralSectionType.CONCLUSION, StructuralSectionType.SOURCES):
        pos = _first_section_position(blocks, closing)
        if pos is not None and pos < end_pos:
            end_pos = pos
    return any(
        isinstance(block, HeadingNode)
        for block in blocks[intro_pos + 1 : end_pos]
    )


def _first_section_position(blocks, section_type) -> int | None:
    for i, block in enumerate(blocks):
        if isinstance(block, StructuralSectionNode) and block.section_type is section_type:
            return i
    return None


def _structural_occurrences(document: Document) -> list[_Occurrence]:
    occurrences: list[_Occurrence] = []
    for position, block in enumerate(document.blocks):
        if isinstance(block, StructuralSectionNode):
            occurrences.append(_Occurrence(block.section_type, block, position))
        elif isinstance(block, AppendixNode):
            occurrences.append(
                _Occurrence(StructuralSectionType.APPENDIX, block, position)
            )
    return occurrences


def _first_by_type(
    occurrences: list[_Occurrence],
) -> dict[StructuralSectionType, _Occurrence]:
    first: dict[StructuralSectionType, _Occurrence] = {}
    for occ in occurrences:
        first.setdefault(occ.section_type, occ)
    return first


def _check_required_sections(
    spec: CompositionSpec,
    first_by_type: dict[StructuralSectionType, _Occurrence],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for section_type in spec.required_sections:
        if section_type in first_by_type:
            continue
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STRUCTURE_REQUIRED_SECTION_MISSING,
                message=f"Required section {section_type.value} is missing",
                severity=Severity.WARNING,
                rule_id=spec.structure_rule_id,
                data={"section": section_type.name},
            )
        )
    return diagnostics


def _check_duplicates(occurrences: list[_Occurrence]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    seen: dict[StructuralSectionType, _Occurrence] = {}
    reported: set[StructuralSectionType] = set()
    for occ in occurrences:
        if occ.section_type is StructuralSectionType.APPENDIX:
            continue
        first = seen.get(occ.section_type)
        if first is None:
            seen[occ.section_type] = occ
            continue
        if occ.section_type in reported:
            continue
        reported.add(occ.section_type)
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STRUCTURE_DUPLICATE_SECTION,
                message=f"Section {occ.section_type.value} appears more than once",
                severity=Severity.WARNING,
                source=first.node.source,
                data={
                    "section": occ.section_type.name,
                    "duplicate_line": _line(occ.node),
                },
            )
        )
    return diagnostics


def _check_ordering(
    first_by_type: dict[StructuralSectionType, _Occurrence],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    appendix = first_by_type.get(StructuralSectionType.APPENDIX)
    sources = first_by_type.get(StructuralSectionType.SOURCES)
    abbreviations = first_by_type.get(StructuralSectionType.ABBREVIATIONS)

    if appendix is not None and sources is not None and appendix.position < sources.position:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STRUCTURE_APPENDIX_BEFORE_SOURCES,
                message="Appendix appears before the list of sources",
                severity=Severity.WARNING,
                source=appendix.node.source,
                data={"actual_position": appendix.position},
            )
        )

    if sources is not None and abbreviations is not None and sources.position < abbreviations.position:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STRUCTURE_SOURCES_BEFORE_ABBREVIATIONS,
                message="List of sources appears before the list of abbreviations",
                severity=Severity.WARNING,
                source=sources.node.source,
                data={"actual_position": sources.position},
            )
        )

    diagnostics.extend(_check_generic_ordering(first_by_type))
    return diagnostics


# Pairs already covered by dedicated diagnostics; skip in generic ordering.
_DEDICATED_PAIRS = {
    (StructuralSectionType.SOURCES, StructuralSectionType.APPENDIX),
    (StructuralSectionType.ABBREVIATIONS, StructuralSectionType.SOURCES),
}


def _check_generic_ordering(
    first_by_type: dict[StructuralSectionType, _Occurrence],
) -> list[Diagnostic]:
    ordered = sorted(
        (occ for occ in first_by_type.values() if occ.section_type in _ORDER_INDEX),
        key=lambda occ: occ.position,
    )
    diagnostics: list[Diagnostic] = []
    for prev, current in zip(ordered, ordered[1:]):
        if _ORDER_INDEX[current.section_type] >= _ORDER_INDEX[prev.section_type]:
            continue
        if (current.section_type, prev.section_type) in _DEDICATED_PAIRS:
            continue
        expected_after = _canonical_predecessor(current.section_type)
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.STRUCTURE_SECTION_OUT_OF_ORDER,
                message=(
                    f"Section {current.section_type.value} is out of canonical order"
                ),
                severity=Severity.WARNING,
                source=current.node.source,
                data={
                    "section": current.section_type.name,
                    "expected_after": expected_after,
                    "actual_position": current.position,
                },
            )
        )
    return diagnostics


def _canonical_predecessor(section_type: StructuralSectionType) -> str | None:
    index = _ORDER_INDEX[section_type]
    if index == 0:
        return None
    return _CANONICAL_ORDER[index - 1].name


def _line(node) -> int | None:
    return node.source.line_start if node.source is not None else None
