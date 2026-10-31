"""Column-width distribution for rendered tables."""

from __future__ import annotations

import pytest

from sfu_converter.infrastructure.table_layout import (
    MAX_COLUMN_SHARE,
    compute_column_widths,
)

TOTAL = 9972


def test_content_volume_drives_column_width():
    widths = compute_column_widths(
        [
            ("№", "Наименование параметра", "Значение"),
            ("1", "Давление в камере сгорания на номинальном режиме", "10"),
            ("2", "Температура", "20"),
        ],
        total_width=TOTAL,
    )

    assert sum(widths) == TOTAL
    assert widths[1] > widths[0]
    assert widths[1] > widths[2]


def test_every_column_fits_its_longest_word():
    widths = compute_column_widths(
        [
            ("Параметр", "Примечание"),
            ("Результат", "суперкалифраджилистикэкспиалидоция"),
        ],
        total_width=TOTAL,
    )

    # 12pt Times New Roman: ~6pt per glyph, i.e. 120 twips.
    word_width = len("суперкалифраджилистикэкспиалидоция") * 120
    assert widths[1] >= word_width


def test_single_column_takes_the_whole_width():
    assert compute_column_widths([("Только колонка",)], total_width=TOTAL) == [TOTAL]


def test_column_share_is_capped():
    widths = compute_column_widths(
        [
            ("Коротко", "Очень длинный текст " * 40),
            ("Ещё", "Ещё длинный текст " * 40),
        ],
        total_width=TOTAL,
    )

    assert sum(widths) == TOTAL
    assert max(widths) <= TOTAL * MAX_COLUMN_SHARE


def test_markup_does_not_widen_a_column():
    plain = compute_column_widths(
        [("Значение", "1"), ("Текст", "2")],
        total_width=TOTAL,
    )
    marked_up = compute_column_widths(
        [("**Значение**", "1"), ("*Текст*", "2")],
        total_width=TOTAL,
    )

    assert plain == marked_up


def test_empty_and_blank_rows_fall_back_to_equal_columns():
    widths = compute_column_widths([("", "", ""), ("", "", "")], total_width=TOTAL)

    assert sum(widths) == TOTAL
    assert len(set(widths)) == 1


@pytest.mark.parametrize("rows", [(), ([],), ([("a",)],)])
def test_degenerate_inputs(rows):
    widths = compute_column_widths(rows, total_width=TOTAL)

    assert len(widths) == (len(rows[0]) if rows else 0)


def test_zero_width_returns_nothing():
    assert compute_column_widths([("a", "b")], total_width=0) == []


def test_ragged_rows_use_the_widest_row():
    widths = compute_column_widths(
        [("a", "b", "c"), ("длинный текст в первой колонке",)],
        total_width=TOTAL,
    )

    assert len(widths) == 3
    assert sum(widths) == TOTAL


def test_many_wide_columns_still_fit_the_table():
    rows = [tuple(f"Показатель номер {index}" for index in range(8))]
    rows.append(tuple("суперкалифраджилистик" for _ in range(8)))

    widths = compute_column_widths(rows, total_width=TOTAL)

    assert sum(widths) == TOTAL
    assert all(width > 0 for width in widths)


def test_water_fill_stops_when_minimums_do_not_fit():
    from sfu_converter.infrastructure.table_layout import _water_fill

    widths = _water_fill([1.0, 1.0], total=100, minimums=[80, 80], maximums=[100, 100])

    assert widths == [80.0, 80.0]


def test_spread_surplus_falls_back_to_the_widest_column():
    from sfu_converter.infrastructure.table_layout import _spread_surplus

    widths = _spread_surplus([10.0, 10.0], [1.0, 1.0], [10, 10], surplus=5.0)

    assert widths == [10.0, 15.0]


def test_spread_surplus_gives_up_on_a_negligible_remainder():
    from sfu_converter.infrastructure.table_layout import _spread_surplus

    widths = _spread_surplus([10.0], [1.0], [10 + 1e-9], surplus=5.0)

    assert widths == pytest.approx([10.0])


def test_rounding_keeps_the_total_and_respects_headroom():
    from sfu_converter.infrastructure.table_layout import _round_to_total

    assert _round_to_total([100.6, 100.6], 200, [1000, 1000]) == [99, 101]
    assert sum(_round_to_total([10.2, 10.2], 21, [10, 10])) == 21
    assert _round_to_total([10.4, 10.4], 21, [100, 100]) == [11, 10]


def test_water_fill_redistributes_after_a_clamp():
    from sfu_converter.infrastructure.table_layout import _water_fill

    widths = _water_fill([1.0, 1000.0], total=100, minimums=[80, 5], maximums=[1000, 1000])

    assert widths == [80.0, 20.0]


def test_water_fill_without_columns_returns_nothing():
    from sfu_converter.infrastructure.table_layout import _water_fill

    assert _water_fill([], total=100, minimums=[], maximums=[]) == []
