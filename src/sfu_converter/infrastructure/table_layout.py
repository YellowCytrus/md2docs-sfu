"""Content-aware column widths for rendered tables.

``python-docx`` gives every new table a fixed grid of equal columns. A table
with one long descriptive column and a couple of short numeric columns therefore
wraps the description into a narrow strip while the numeric columns keep most
of their width empty. :func:`compute_column_widths` spreads the available text
width over the columns in proportion to their content and keeps every column
wide enough to avoid breaking words in the middle.

All widths are measured in twips (1 pt = 20 twips), the unit ``w:gridCol`` and
``w:tcW`` use.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sfu_converter.domain.inline_markup import strip_inline_markup

#: EMU per twip (1 pt = 20 twips, 1 pt = 12700 EMU).
EMU_PER_TWIP = 635

#: Width estimate used for minimum widths, as a fraction of the font size per
#: glyph. Underestimating a minimum breaks words mid-token; over-wide minimums
#: only borrow width from flexible columns, so the estimate errs wide.
MIN_CHAR_WIDTH_EM = 0.6

#: Word's default cell padding: 108 twips on each side.
CELL_HORIZONTAL_PADDING_TWIPS = 216

#: A column never gets narrower than this many characters.
MIN_COLUMN_CHARS = 4

#: A single column never takes more than this share of the table width.
MAX_COLUMN_SHARE = 0.7

#: Longer unbreakable tokens stop widening a column's minimum at this length,
#: so one pasted URL cannot claim a third of the table.
MAX_MINIMUM_CHARS = 32


@dataclass(frozen=True)
class _ColumnStats:
    """Content measurements of one table column."""

    weight: float
    longest_token: int


def compute_column_widths(
    rows: Sequence[Sequence[str]],
    *,
    total_width: int,
    font_size_pt: float = 12.0,
) -> list[int]:
    """Return per-column widths in twips that sum up to ``total_width``.

    Columns holding more text receive more width; columns that only carry short
    values (numbers, units, counters) shrink down to their content. Every column
    stays wide enough for its longest token plus cell padding.
    """

    column_count = max((len(row) for row in rows), default=0)
    if column_count <= 0 or total_width <= 0:
        return []
    if column_count == 1:
        return [int(total_width)]

    stats = [_column_stats(rows, index) for index in range(column_count)]
    weights = [column.weight for column in stats]
    minimums = [_minimum_width(column, total_width, font_size_pt) for column in stats]
    maximum = max(1, int(total_width * MAX_COLUMN_SHARE))
    maximums = [max(maximum, minimum) for minimum in minimums]
    return _distribute(weights, int(total_width), minimums, maximums)


def _column_stats(rows: Sequence[Sequence[str]], index: int) -> _ColumnStats:
    lengths: list[int] = []
    longest_token = 0
    for row in rows:
        text = strip_inline_markup(row[index]).strip() if index < len(row) else ""
        lengths.append(len(text))
        tokens = [len(token) for token in text.split()]
        if tokens:
            longest_token = max(longest_token, max(tokens))
    # The mean keeps a column with many medium cells wide, the longest cell keeps
    # a single paragraph-long cell from becoming a narrow ribbon.
    weight = 0.5 * (sum(lengths) / len(lengths)) + 0.5 * max(lengths)
    return _ColumnStats(max(weight, float(MIN_COLUMN_CHARS)), longest_token)


def _minimum_width(column: _ColumnStats, total_width: int, font_size_pt: float) -> int:
    chars = max(MIN_COLUMN_CHARS, min(column.longest_token + 1, MAX_MINIMUM_CHARS))
    width = _chars_to_twips(chars * MIN_CHAR_WIDTH_EM, font_size_pt) + CELL_HORIZONTAL_PADDING_TWIPS
    return min(width, max(1, int(total_width * 0.4)))


def _chars_to_twips(chars: float, font_size_pt: float) -> int:
    return int(round(chars * font_size_pt * 20))


def _distribute(weights: list[float], total: int, minimums: list[int], maximums: list[int]) -> list[int]:
    """Split ``total`` proportionally to ``weights`` within the given bounds."""

    if sum(minimums) > total:
        # Not even the minimums fit: keep them proportional instead of clipping.
        scale = total / sum(minimums)
        minimums = [max(1, int(minimum * scale)) for minimum in minimums]

    widths = _water_fill(weights, total, minimums, maximums)
    surplus = total - sum(widths)
    if surplus > 0:
        # Every column hit a bound before the budget was spent; give the rest to
        # the columns that still have headroom.
        widths = _spread_surplus(widths, weights, maximums, surplus)
    return _round_to_total(widths, total, maximums)


def _water_fill(weights: list[float], total: int, minimums: list[int], maximums: list[int]) -> list[float]:
    count = len(weights)
    widths = [0.0] * count
    free = list(range(count))
    budget = float(total)
    while free:
        weight_sum = sum(weights[index] for index in free)
        clamped = False
        for index in list(free):
            share = budget * _fraction(weights, index, weight_sum)
            if share < minimums[index]:
                widths[index] = float(minimums[index])
            elif share > maximums[index]:
                widths[index] = float(maximums[index])
            else:
                continue
            free.remove(index)
            clamped = True
        if not clamped:
            weight_sum = sum(weights[index] for index in free)
            for index in free:
                widths[index] = budget * _fraction(weights, index, weight_sum)
            break
        budget = total - sum(widths)
        if not free:
            break
    return widths


def _spread_surplus(
    widths: list[float],
    weights: list[float],
    maximums: list[int],
    surplus: float,
) -> list[float]:
    widths = list(widths)
    while surplus > 1e-6:
        roomy = [index for index in range(len(widths)) if widths[index] < maximums[index]]
        if not roomy:
            widths[-1] += surplus
            break
        weight_sum = sum(weights[index] for index in roomy)
        added = 0.0
        for index in roomy:
            share = surplus * _fraction(weights, index, weight_sum)
            step = min(share, maximums[index] - widths[index])
            widths[index] += step
            added += step
        if added <= 1e-6:
            break
        surplus -= added
    return widths


def _fraction(weights: list[float], index: int, weight_sum: float) -> float:
    # Weights are floored at MIN_COLUMN_CHARS, so the sum is never zero.
    return weights[index] / weight_sum


def _round_to_total(widths: list[float], total: int, maximums: list[int]) -> list[int]:
    rounded = [max(1, int(round(width))) for width in widths]
    delta = total - sum(rounded)
    if delta == 0:
        return rounded
    candidates = list(range(len(rounded)))
    if delta > 0:
        # Growing past the cap is still better than leaving the table short.
        candidates = [index for index in candidates if rounded[index] < maximums[index]] or candidates
    target = max(candidates, key=rounded.__getitem__)
    rounded[target] = max(1, rounded[target] + delta)
    return rounded
