from docx.shared import Cm

from sfu_converter.domain.ast_nodes import ListType
from sfu_converter.infrastructure.list_layout import (
    RUSSIAN_LIST_LETTERS,
    list_item_layout,
    list_marker,
)


def assert_close(actual, expected) -> None:
    assert abs(actual - expected) < 1000


def test_russian_letter_sequence_excludes_disallowed_letters():
    disallowed = set("ёзйочьыъ")

    assert disallowed.isdisjoint(RUSSIAN_LIST_LETTERS)
    assert RUSSIAN_LIST_LETTERS[:8] == ("а", "б", "в", "г", "д", "е", "ж", "и")


def test_list_marker_uses_standard_markers():
    assert list_marker(ListType.BULLET, 0) == "-"
    assert list_marker(ListType.LETTERED, 7) == "и)"
    assert list_marker(ListType.NUMBERED, 1) == "2)"


def test_nested_numeric_layout_is_half_centimeter_past_parent():
    parent = list_item_layout(ListType.LETTERED, level=0)
    nested = list_item_layout(ListType.NUMBERED, level=1)

    assert_close(parent.left_indent, Cm(1.25))
    assert_close(parent.first_line_indent, Cm(-0.5))
    assert_close(nested.left_indent, Cm(1.75))
    assert_close(nested.first_line_indent, Cm(-0.5))
