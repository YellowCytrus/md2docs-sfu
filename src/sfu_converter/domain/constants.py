"""Shared SFU converter constants.

This module holds literals that are used across parser, renderer, validator,
and registry glue. Rule-specific numeric values still live in the formatting
registry; these names are for cross-cutting defaults and punctuation.
"""

from __future__ import annotations

DEFAULT_PROFILE_NAME = "common"

EM_DASH = "—"
EN_DASH = "–"
DASH_SEPARATOR = f" {EM_DASH} "

APPENDIX_TITLE = "ПРИЛОЖЕНИЕ"
EXCLUDED_APPENDIX_LETTERS: tuple[str, ...] = ("Ё", "З", "Й", "О", "Ч", "Ь", "Ы", "Ъ")
APPENDIX_LETTERS: tuple[str, ...] = (
    "А",
    "Б",
    "В",
    "Г",
    "Д",
    "Е",
    "Ж",
    "И",
    "К",
    "Л",
    "М",
    "Н",
    "П",
    "Р",
    "С",
    "Т",
    "У",
    "Ф",
    "Х",
    "Ц",
    "Ш",
    "Щ",
    "Э",
    "Ю",
    "Я",
)
RUSSIAN_LIST_LETTERS: tuple[str, ...] = tuple(letter.lower() for letter in APPENDIX_LETTERS)
DISALLOWED_RUSSIAN_LIST_LETTERS = frozenset(letter.lower() for letter in EXCLUDED_APPENDIX_LETTERS)

DEFAULT_CITY = "Красноярск"
DEFAULT_YEAR = ""
SIGNATURE_LINE = "____________"
DEFAULT_APPROVAL_DATE = "«___» _____________ 20__ г."

NO_INDENT_CM_VALUE = 0
FIRST_LINE_INDENT_CM_VALUE = 1.25
LIST_HANGING_INDENT_CM_VALUE = -0.5
LIST_HANGING_WIDTH_CM_VALUE = 0.5
NUMBERED_LIST_LEFT_INDENT_CM_VALUE = 1.75
ABBREVIATIONS_COLUMN_WIDTH_CM_VALUES = (4, 13)
