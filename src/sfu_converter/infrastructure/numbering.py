"""Section- and appendix-aware numbering for tables, figures, formulas, headings.

Replaces the per-counter scalars previously held on the renderer. A single
:class:`NumberingContext` instance tracks heading section numbers (H1..H6),
the current appendix (if any), and three element counters that may be reset
per section or scoped per appendix depending on the active
:class:`NumberingMode`.

The context is built once per render call by
:func:`build_numbering_context`, which inspects the active formatting profile
to decide whether each element kind (formula, table, figure) uses GLOBAL or
SECTION numbering. Inside an appendix the counters are always re-scoped on
the appendix letter, regardless of the mode the profile selected for the
body of the document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from sfu_converter.domain.ast_nodes import HeadingLevel
from sfu_converter.domain.formatting import FormattingProfile, RuleStatus


class NumberingMode(Enum):
    """How element numbers (formula/table/figure) relate to section numbers."""

    GLOBAL = "global"
    SECTION = "section"
    APPENDIX = "appendix"


@dataclass
class _CounterScope:
    """Counters that reset together when the surrounding scope changes."""

    section_numbers: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    formula_counter: int = 0
    table_counter: int = 0
    figure_counter: int = 0


@dataclass(frozen=True)
class NumberingModes:
    """Mode selection for each numbered element kind."""

    formula: NumberingMode = NumberingMode.GLOBAL
    table: NumberingMode = NumberingMode.GLOBAL
    figure: NumberingMode = NumberingMode.GLOBAL


class NumberingContext:
    """Track section numbers and element counters during rendering."""

    def __init__(self, modes: NumberingModes | None = None) -> None:
        self.modes = modes or NumberingModes()
        self._body = _CounterScope()
        self._appendix_stack: list[tuple[str, _CounterScope]] = []

    # -- scope helpers -------------------------------------------------

    @property
    def appendix_letter(self) -> str | None:
        return self._appendix_stack[-1][0] if self._appendix_stack else None

    @property
    def _scope(self) -> _CounterScope:
        if self._appendix_stack:
            return self._appendix_stack[-1][1]
        return self._body

    def enter_appendix(self, letter: str) -> None:
        """Push a fresh counter scope identified by ``letter`` (e.g. ``А``)."""

        self._appendix_stack.append((letter, _CounterScope()))

    def leave_appendix(self) -> None:
        if self._appendix_stack:
            self._appendix_stack.pop()

    # -- heading numbering --------------------------------------------

    def next_section_number(self, level: HeadingLevel | int) -> str:
        """Advance the heading counter for ``level`` and return the formatted number.

        Inside an appendix the leading component is the appendix letter rather
        than a digit (e.g. ``А.1``, ``А.1.1``).
        """

        level_value = level.value if isinstance(level, HeadingLevel) else int(level)
        if level_value < 1:
            raise ValueError(f"Unsupported heading level: {level_value}")

        index = level_value - 1
        section_numbers = self._scope.section_numbers
        while len(section_numbers) < level_value:
            section_numbers.append(0)

        for parent_index in range(index):
            if section_numbers[parent_index] == 0:
                section_numbers[parent_index] = 1

        section_numbers[index] += 1
        for lower_index in range(index + 1, len(section_numbers)):
            section_numbers[lower_index] = 0

        # Reset element counters when section_numbering is on. Appendix scope
        # is independent and always per-appendix. In section mode the counters
        # reset only on a level-1 heading (section), not on subsections.
        if self._appendix_stack or (self._is_section_mode() and level_value == 1):
            scope = self._scope
            scope.formula_counter = 0
            scope.table_counter = 0
            scope.figure_counter = 0

        digits = ".".join(str(part) for part in section_numbers[:level_value])
        if self._appendix_stack:
            return f"{self.appendix_letter}.{digits}"
        return digits

    def _is_section_mode(self) -> bool:
        return (
            self.modes.formula is NumberingMode.SECTION
            or self.modes.table is NumberingMode.SECTION
            or self.modes.figure is NumberingMode.SECTION
        )

    # -- element numbering --------------------------------------------

    def next_formula_number(self) -> str:
        return self._next_element_number(
            mode=self.modes.formula,
            attribute="formula_counter",
        )

    def next_table_number(self) -> str:
        return self._next_element_number(
            mode=self.modes.table,
            attribute="table_counter",
        )

    def next_figure_number(self) -> str:
        return self._next_element_number(
            mode=self.modes.figure,
            attribute="figure_counter",
        )

    def _next_element_number(self, *, mode: NumberingMode, attribute: str) -> str:
        scope = self._scope
        count = getattr(scope, attribute) + 1
        setattr(scope, attribute, count)

        if self._appendix_stack:
            return f"{self.appendix_letter}.{count}"

        if mode is NumberingMode.SECTION and scope.section_numbers[0] > 0:
            return f"{scope.section_numbers[0]}.{count}"

        return str(count)


def _profile_section_mode(profile: FormattingProfile | None, rule_suffix: str) -> NumberingMode:
    """Pick GLOBAL/SECTION based on a profile's ``*.section_numbering`` rule.

    Walks every rule whose id ends with ``rule_suffix``; if any rule is
    ``IMPLEMENTED`` with ``default_enabled`` set (defaults to True), the
    section-based mode wins. This lets a profile-specific override flip the
    mode on without removing the GLOBAL ``common.*.section_numbering`` rule.
    """

    if profile is None:
        return NumberingMode.GLOBAL
    enabled = False
    for rule in profile.rules:
        if not rule.id.endswith(rule_suffix):
            continue
        if rule.renderer_status is not RuleStatus.IMPLEMENTED:
            continue
        if rule.parameters.get("default_enabled", True):
            enabled = True
    return NumberingMode.SECTION if enabled else NumberingMode.GLOBAL


def build_numbering_context(profile: FormattingProfile | None) -> NumberingContext:
    """Construct a :class:`NumberingContext` tuned to ``profile``."""

    modes = NumberingModes(
        formula=_profile_section_mode(profile, ".formula.section_numbering"),
        table=_profile_section_mode(profile, ".table.section_numbering"),
        figure=_profile_section_mode(profile, ".figure.section_numbering"),
    )
    return NumberingContext(modes=modes)
