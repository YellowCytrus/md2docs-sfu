"""Inline emphasis markup shared by the parser and the table-cell renderer."""

from __future__ import annotations

from sfu_converter.domain.inline_markup import split_inline_markup, strip_inline_markup


def _flags(text: str) -> list[tuple[str, bool, bool]]:
    return [(run.text, run.bold, run.italic) for run in split_inline_markup(text)]


def test_plain_text_is_a_single_run():
    assert _flags("обычный текст") == [("обычный текст", False, False)]


def test_bold_italic_and_both_are_split_into_runs():
    assert _flags("**жирный** и *курсив* и ***оба***") == [
        ("жирный", True, False),
        (" и ", False, False),
        ("курсив", False, True),
        (" и ", False, False),
        ("оба", True, True),
    ]


def test_text_after_markup_keeps_its_own_run():
    assert _flags("**жирный** хвост") == [("жирный", True, False), (" хвост", False, False)]


def test_markers_that_do_not_close_stay_literal():
    assert _flags("2 * 3 = 6") == [("2 * 3 = 6", False, False)]


def test_empty_text_yields_one_empty_run():
    assert _flags("") == [("", False, False)]


def test_source_span_is_propagated():
    runs = split_inline_markup("**a** b")

    assert all(run.source is None for run in runs)


def test_strip_inline_markup_keeps_the_text():
    assert strip_inline_markup("**жирный** и *курсив*, и ***оба***") == "жирный и курсив, и оба"
