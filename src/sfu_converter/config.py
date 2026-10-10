"""Legacy ``SIBFUConfig`` compatibility layer over the formatting registry.

The class attributes are populated from the registry at import time. New code
should reach for ``sfu_converter.registry`` directly; this module remains so
existing callers (renderer, validator, image utils) keep working unchanged.
"""

from __future__ import annotations

from sfu_converter.registry.loader import build_legacy_config

_LEGACY_CONFIG = build_legacy_config()


class PathConfig:
    """Canonical relative directories and filenames used by legacy entrypoints."""

    EXAMPLES_DIR = "examples"
    TEMPLATES_DIR = "templates"
    RESULTS_DIR = "results"
    IMAGES_DIR = "images"
    LOGS_DIR = "logs"
    LOG_FILENAME = "converter.log"


class MeasurementConfig:
    """Document-unit conversion constants shared by rendering helpers."""

    EMU_PER_INCH = 914400
    EMU_PER_CM = 360000
    DEFAULT_DPI = 96


class SyntaxConfig:
    """Syntax-level constants shared by parser implementations."""

    FIGURE_CAPTION_PREFIXES = ("Рисунок", "Figure", "Рис.")


class SIBFUConfig:
    """Конфигурация стандартов оформления СФУ.

    Compatibility shim. Values come from the rule registry under
    ``sfu_converter.registry``; do not edit constants here.
    """

    FONT_NAME = _LEGACY_CONFIG["FONT_NAME"]
    FONT_SIZE = _LEGACY_CONFIG["FONT_SIZE"]
    FONT_COLOR_RGB = _LEGACY_CONFIG["FONT_COLOR_RGB"]
    LINE_SPACING_NORMAL = _LEGACY_CONFIG["LINE_SPACING_NORMAL"]
    ALIGNMENT = _LEGACY_CONFIG["ALIGNMENT"]
    FIRST_LINE_INDENT = _LEGACY_CONFIG["FIRST_LINE_INDENT"]

    H1 = _LEGACY_CONFIG["H1"]
    H2 = _LEGACY_CONFIG["H2"]
    H3 = _LEGACY_CONFIG["H3"]
    H4 = _LEGACY_CONFIG["H4"]
    LIST_ITEM = _LEGACY_CONFIG["LIST_ITEM"]
    STRUCTURAL_SECTION = _LEGACY_CONFIG["STRUCTURAL_SECTION"]
    STRUCTURAL_HEADINGS = _LEGACY_CONFIG["STRUCTURAL_HEADINGS"]

    CAPTION_IMAGE = _LEGACY_CONFIG["CAPTION_IMAGE"]
    CAPTION_TABLE = _LEGACY_CONFIG["CAPTION_TABLE"]

    EMPTY_BEFORE_HEADER = _LEGACY_CONFIG["EMPTY_BEFORE_HEADER"]
    EMPTY_AFTER_HEADER = _LEGACY_CONFIG["EMPTY_AFTER_HEADER"]
    EMPTY_BEFORE_IMAGE = _LEGACY_CONFIG["EMPTY_BEFORE_IMAGE"]
    EMPTY_AFTER_IMAGE = _LEGACY_CONFIG["EMPTY_AFTER_IMAGE"]
    EMPTY_BEFORE_TABLE = _LEGACY_CONFIG["EMPTY_BEFORE_TABLE"]
    EMPTY_AFTER_TABLE = _LEGACY_CONFIG["EMPTY_AFTER_TABLE"]
    EMPTY_BEFORE_FORMULA = _LEGACY_CONFIG["EMPTY_BEFORE_FORMULA"]
    EMPTY_AFTER_FORMULA = _LEGACY_CONFIG["EMPTY_AFTER_FORMULA"]
    FORMULA = _LEGACY_CONFIG["FORMULA"]
    FORMULA_EXPLANATION = _LEGACY_CONFIG["FORMULA_EXPLANATION"]
    BIBLIOGRAPHY_ENTRY = _LEGACY_CONFIG["BIBLIOGRAPHY_ENTRY"]

    MARGINS = _LEGACY_CONFIG["MARGINS"]
    PAGE_NUMBERING = _LEGACY_CONFIG["PAGE_NUMBERING"]
    IMAGE = _LEGACY_CONFIG["IMAGE"]
    TABLE_CELL_PADDING = _LEGACY_CONFIG["TABLE_CELL_PADDING"]
    TABLE = _LEGACY_CONFIG["TABLE"]
