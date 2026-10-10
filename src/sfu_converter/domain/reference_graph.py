from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from sfu_converter.domain.ast_nodes import (
    AppendixNode,
    BibliographyEntryNode,
    CitationNode,
    Document,
    FigureNode,
    FootnoteAnchor,
    FootnoteNode,
    FormulaNode,
    HeadingNode,
    ParagraphNode,
    RawBlockNode,
    ReferenceNode,
    SourceRecordNode,
    SourceSpan,
    TableCaptionNode,
    TableNode,
    TextRun,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity


class ReferenceTargetKind(str, Enum):
    FIGURE = "figure"
    TABLE = "table"
    FORMULA = "formula"
    APPENDIX = "appendix"
    SOURCE = "source"
    FOOTNOTE = "footnote"
    SECTION = "section"
    FORM = "form"


@dataclass(frozen=True)
class ReferenceDefinition:
    kind: ReferenceTargetKind
    canonical: str
    aliases: tuple[str, ...]
    source: SourceSpan | None = None
    position: int = 0


@dataclass(frozen=True)
class ReferenceSite:
    kind: ReferenceTargetKind
    key: str
    raw: str
    source: SourceSpan | None = None
    position: int = 0

    @property
    def target(self) -> str:
        return f"{self.kind.value}:{self.key}"


@dataclass(frozen=True)
class ReferenceEdge:
    site: ReferenceSite
    definition: ReferenceDefinition


class ReferenceGraph:
    def __init__(
        self,
        definitions: Iterable[ReferenceDefinition],
        sites: Iterable[ReferenceSite],
    ) -> None:
        self.definitions = tuple(definitions)
        self.sites = tuple(sites)
        self._definitions_by_alias: dict[tuple[ReferenceTargetKind, str], list[ReferenceDefinition]] = defaultdict(list)
        for definition in self.definitions:
            for alias in definition.aliases:
                self._definitions_by_alias[(definition.kind, _normalize_key(alias))].append(definition)

        edges: list[ReferenceEdge] = []
        for site in self.sites:
            matches = self._definitions_by_alias.get((site.kind, _normalize_key(site.key)), [])
            if len(matches) == 1:
                edges.append(ReferenceEdge(site=site, definition=matches[0]))
        self.edges = tuple(edges)

    def references_to(self, kind: ReferenceTargetKind, key: str) -> bool:
        canonical = self._canonical_for(kind, key)
        return any(edge.definition.kind is kind and edge.definition.canonical == canonical for edge in self.edges)

    def diagnostics(self) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        diagnostics.extend(self._ambiguous_definition_diagnostics())
        diagnostics.extend(self._unresolved_reference_diagnostics())
        diagnostics.extend(self._unused_definition_diagnostics())
        return diagnostics

    def first_reference_position(self, kind: ReferenceTargetKind, key: str) -> int | None:
        canonical = self._canonical_for(kind, key)
        positions = [
            edge.site.position
            for edge in self.edges
            if edge.definition.kind is kind and edge.definition.canonical == canonical
        ]
        return min(positions) if positions else None

    def _canonical_for(self, kind: ReferenceTargetKind, key: str) -> str:
        normalized = _normalize_key(key)
        matches = self._definitions_by_alias.get((kind, normalized), [])
        if matches:
            return matches[0].canonical
        return key

    def _ambiguous_definition_diagnostics(self) -> list[Diagnostic]:
        diagnostics = []
        seen: set[tuple[ReferenceTargetKind, str]] = set()
        for (kind, alias), definitions in self._definitions_by_alias.items():
            if len(definitions) < 2 or (kind, alias) in seen:
                continue
            seen.add((kind, alias))
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.REFERENCE_AMBIGUOUS,
                    message=f"Reference target '{kind.value}:{alias}' has multiple definitions",
                    severity=Severity.ERROR,
                    rule_id=_rule_id_for_kind(kind),
                    source=definitions[1].source,
                    target=f"{kind.value}:{alias}",
                )
            )
        return diagnostics

    def _unresolved_reference_diagnostics(self) -> list[Diagnostic]:
        diagnostics = []
        for site in self.sites:
            matches = self._definitions_by_alias.get((site.kind, _normalize_key(site.key)), [])
            if matches:
                continue
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.REFERENCE_UNRESOLVED,
                    message=f"Reference '{site.raw}' does not resolve to a {site.kind.value}",
                    severity=Severity.ERROR,
                    rule_id=_rule_id_for_kind(site.kind),
                    source=site.source,
                    target=site.target,
                )
            )
        return diagnostics

    def _unused_definition_diagnostics(self) -> list[Diagnostic]:
        used = {(edge.definition.kind, edge.definition.canonical) for edge in self.edges}
        diagnostics = []
        for definition in self.definitions:
            key = (definition.kind, definition.canonical)
            if key in used:
                continue
            code = _unused_code_for_kind(definition.kind)
            if code is None:
                continue
            diagnostics.append(
                Diagnostic(
                    code=code,
                    message=f"{definition.kind.value.capitalize()} '{definition.canonical}' is never referenced",
                    severity=Severity.WARNING,
                    rule_id=_rule_id_for_kind(definition.kind),
                    source=definition.source,
                    target=definition.canonical,
                )
            )
        return diagnostics


def build_reference_graph(document: Document) -> ReferenceGraph:
    builder = _ReferenceGraphBuilder()
    builder.visit(document.blocks)
    return ReferenceGraph(builder.definitions, builder.sites)


class _ReferenceGraphBuilder:
    def __init__(self) -> None:
        self.definitions: list[ReferenceDefinition] = []
        self.sites: list[ReferenceSite] = []
        self._position = 0
        self._figure_count = 0
        self._table_count = 0
        self._formula_count = 0

    def visit(self, blocks: Iterable) -> None:
        for block in blocks:
            self._position += 1
            position = self._position
            self._collect_definition(block, position)
            self._collect_sites(block, position)
            if isinstance(block, AppendixNode):
                self.visit(block.blocks)

    def _collect_definition(self, block, position: int) -> None:
        if isinstance(block, FigureNode):
            raw_number = getattr(block, "number", None)
            self._figure_count += 1
            if not block.id and raw_number is None:
                return
            number = _definition_number(raw_number, self._figure_count)
            canonical = block.id or f"figure:{number}"
            self._add_definition(ReferenceTargetKind.FIGURE, canonical, block.source, position, block.id, number)
        elif isinstance(block, TableNode):
            self._table_count += 1
            if not block.id and block.number is None:
                return
            number = _definition_number(block.number, self._table_count)
            canonical = block.id or f"table:{number}"
            self._add_definition(ReferenceTargetKind.TABLE, canonical, block.source, position, block.id, number)
        elif isinstance(block, FormulaNode):
            self._formula_count += 1
            if not block.id and block.number is None:
                return
            number = _definition_number(block.number, self._formula_count)
            canonical = block.id or f"formula:{number}"
            self._add_definition(ReferenceTargetKind.FORMULA, canonical, block.source, position, block.id, number)
        elif isinstance(block, AppendixNode):
            aliases = [block.id, block.letter]
            if block.letter:
                aliases.extend((block.letter.lower(), f"app:{block.letter.lower()}"))
            canonical = block.id or (f"app:{block.letter.lower()}" if block.letter else f"appendix:{position}")
            self._add_definition(ReferenceTargetKind.APPENDIX, canonical, block.source, position, *aliases)
        elif isinstance(block, (BibliographyEntryNode, SourceRecordNode)):
            canonical = f"source:{block.number}"
            self._add_definition(
                ReferenceTargetKind.SOURCE,
                canonical,
                block.source,
                position,
                str(block.number),
                canonical,
            )
        elif isinstance(block, FootnoteNode):
            self._add_definition(ReferenceTargetKind.FOOTNOTE, block.marker, block.source, position, block.marker)
        elif isinstance(block, HeadingNode) and block.number and block.number != "auto":
            self._add_definition(ReferenceTargetKind.SECTION, block.number, block.source, position, block.number)

    def _collect_sites(self, block, position: int) -> None:
        if isinstance(block, ParagraphNode):
            for run in block.runs:
                if isinstance(run, CitationNode):
                    for citation in run.citations:
                        self._add_site(
                            ReferenceTargetKind.SOURCE,
                            str(citation.number),
                            f"source:{citation.number}",
                            run.source or block.source,
                            position,
                        )
                elif isinstance(run, FootnoteAnchor):
                    self._add_site(ReferenceTargetKind.FOOTNOTE, run.marker, run.marker, run.source, position)
                elif isinstance(run, TextRun):
                    self._scan_text(run.text, run.source or block.source, position)
        elif isinstance(block, ReferenceNode):
            kind, key = _parse_explicit_target(block.target)
            self._add_site(kind, key, block.target, block.source, position)
        elif isinstance(block, RawBlockNode):
            self._scan_text(block.text, block.source, position)
        elif isinstance(block, TableCaptionNode):
            self._scan_text(block.text, block.source, position)

    def _scan_text(self, text: str, source: SourceSpan | None, position: int) -> None:
        for kind, pattern in _TEXT_REFERENCE_PATTERNS:
            for match in pattern.finditer(text):
                key = match.group("key")
                self._add_site(kind, key, match.group(0), source, position)

    def _add_definition(
        self,
        kind: ReferenceTargetKind,
        canonical: str,
        source: SourceSpan | None,
        position: int,
        *aliases: str | None,
    ) -> None:
        unique_aliases = _unique_aliases(canonical, *aliases)
        self.definitions.append(
            ReferenceDefinition(
                kind=kind,
                canonical=canonical,
                aliases=unique_aliases,
                source=source,
                position=position,
            )
        )

    def _add_site(
        self,
        kind: ReferenceTargetKind,
        key: str,
        raw: str,
        source: SourceSpan | None,
        position: int,
    ) -> None:
        self.sites.append(ReferenceSite(kind=kind, key=key, raw=raw, source=source, position=position))


_REFERENCE_KEY = r"(?P<key>[0-9A-Za-zА-Яа-яЁё:_.-]+)"
_TEXT_REFERENCE_PATTERNS = (
    (
        ReferenceTargetKind.FIGURE,
        re.compile(rf"\((?:см\.\s*)?(?:рисунок|рис\.)\s+{_REFERENCE_KEY}\)", re.IGNORECASE),
    ),
    (
        ReferenceTargetKind.TABLE,
        re.compile(rf"\((?:см\.\s*)?(?:таблица|таблицу|табл\.)\s+{_REFERENCE_KEY}\)", re.IGNORECASE),
    ),
    (
        ReferenceTargetKind.FORMULA,
        re.compile(rf"\((?:формул[аые]\s*)?\({_REFERENCE_KEY}\)\)", re.IGNORECASE),
    ),
    (
        ReferenceTargetKind.APPENDIX,
        re.compile(rf"\((?:см\.\s*)?(?:приложение|прил\.)\s+{_REFERENCE_KEY}\)", re.IGNORECASE),
    ),
)


def _parse_explicit_target(target: str) -> tuple[ReferenceTargetKind, str]:
    normalized = target.strip()
    for prefix, kind in (
        ("figure:", ReferenceTargetKind.FIGURE),
        ("table:", ReferenceTargetKind.TABLE),
        ("formula:", ReferenceTargetKind.FORMULA),
        ("appendix:", ReferenceTargetKind.APPENDIX),
        ("source:", ReferenceTargetKind.SOURCE),
        ("footnote:", ReferenceTargetKind.FOOTNOTE),
        ("section:", ReferenceTargetKind.SECTION),
        ("form:", ReferenceTargetKind.FORM),
    ):
        if normalized.casefold().startswith(prefix):
            return kind, normalized[len(prefix) :]
    if normalized.casefold().startswith("fig:"):
        return ReferenceTargetKind.FIGURE, normalized
    if normalized.casefold().startswith("tbl:"):
        return ReferenceTargetKind.TABLE, normalized
    if normalized.casefold().startswith(("eq:", "formula:")):
        return ReferenceTargetKind.FORMULA, normalized
    if normalized.casefold().startswith("app:"):
        return ReferenceTargetKind.APPENDIX, normalized
    return ReferenceTargetKind.SECTION, normalized


def _definition_number(number: str | None, fallback: int) -> str:
    if number and number != "auto":
        return str(number)
    return str(fallback)


def _unique_aliases(canonical: str, *aliases: str | None) -> tuple[str, ...]:
    values: list[str] = []
    normalized_values: set[str] = set()
    for alias in (canonical, *aliases):
        if not alias:
            continue
        normalized = _normalize_key(alias)
        if normalized not in normalized_values:
            values.append(alias)
            normalized_values.add(normalized)
    return tuple(values)


def _normalize_key(key: str) -> str:
    return " ".join(str(key).strip().casefold().split())


def _unused_code_for_kind(kind: ReferenceTargetKind) -> str | None:
    if kind in {ReferenceTargetKind.FIGURE, ReferenceTargetKind.TABLE, ReferenceTargetKind.FORMULA}:
        return DiagnosticCodes.REFERENCE_OBJECT_UNUSED
    if kind is ReferenceTargetKind.SOURCE:
        return DiagnosticCodes.REFERENCE_BIBLIOGRAPHY_UNUSED
    if kind is ReferenceTargetKind.APPENDIX:
        return DiagnosticCodes.REFERENCE_APPENDIX_UNUSED
    return None


def _rule_id_for_kind(kind: ReferenceTargetKind) -> str:
    if kind is ReferenceTargetKind.SOURCE:
        return "common.reference.cross_check"
    if kind is ReferenceTargetKind.APPENDIX:
        return "common.appendix.in_text_reference"
    return "common.reference.figure_table_formula"
