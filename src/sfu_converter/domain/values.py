from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Length:
    """A numeric length with an explicit unit."""

    value: float
    unit: str


@dataclass(frozen=True)
class Spacing:
    """Paragraph spacing values expressed in points and line multiplier."""

    before_pt: float = 0
    after_pt: float = 0
    line: float = 1.0


@dataclass(frozen=True)
class Margins:
    """Page margins expressed in centimeters."""

    top_cm: float
    bottom_cm: float
    left_cm: float
    right_cm: float
