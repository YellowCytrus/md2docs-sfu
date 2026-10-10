from __future__ import annotations

from dataclasses import dataclass

from docx.shared import Cm

from sfu_converter.domain.constants import (
    DISALLOWED_RUSSIAN_LIST_LETTERS,
    FIRST_LINE_INDENT_CM_VALUE,
    LIST_HANGING_WIDTH_CM_VALUE,
    RUSSIAN_LIST_LETTERS,
)
from sfu_converter.infrastructure.docx_measurements import LIST_HANGING_INDENT_CM, LIST_HANGING_WIDTH_CM
from sfu_converter.domain.ast_nodes import ListType


RUSSIAN_LIST_LETTER_INDEX = {letter: index for index, letter in enumerate(RUSSIAN_LIST_LETTERS)}


@dataclass(frozen=True)
class ListItemLayout:
    left_indent: object
    first_line_indent: object
    hanging_indent: object


def list_marker(list_type: ListType, index: int) -> str:
    if list_type is ListType.BULLET:
        return "-"
    if list_type is ListType.NUMBERED:
        return f"{index + 1})"
    if list_type is ListType.LETTERED:
        if 0 <= index < len(RUSSIAN_LIST_LETTERS):
            return f"{RUSSIAN_LIST_LETTERS[index]})"
        return f"{index + 1})"
    raise ValueError(f"Unsupported list type: {list_type}")


def list_item_layout(list_type: ListType, *, level: int = 0) -> ListItemLayout:
    # The marker must sit *after* the red-line (first-line) indent, so the
    # wrapped body text hangs one marker-width further to the right.
    left_indent_cm = FIRST_LINE_INDENT_CM_VALUE + LIST_HANGING_WIDTH_CM_VALUE + max(level, 0) * 0.5
    return ListItemLayout(
        left_indent=Cm(left_indent_cm),
        first_line_indent=LIST_HANGING_INDENT_CM,
        hanging_indent=LIST_HANGING_WIDTH_CM,
    )


def apply_list_item_layout(paragraph, list_type: ListType, *, level: int = 0) -> None:
    layout = list_item_layout(list_type, level=level)
    paragraph.paragraph_format.left_indent = layout.left_indent
    paragraph.paragraph_format.first_line_indent = layout.first_line_indent
