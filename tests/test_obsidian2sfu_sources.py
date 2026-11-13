"""Regression tests: the bibliography must be emitted exactly once.

# rule: common.bibliography.single_section
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"

CONFIG_SOURCES = ["Источник из конфига А", "Источник из конфига Б"]


def _load_converter_module():
    spec = importlib.util.spec_from_file_location("obsidian2sfu_sources_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _convert(module, markdown: str, sources=None):
    converter = module.MarkdownConverter(
        {
            "meta": {"profile": "lab_practical_project_reports"},
            "meta_items": [],
            "sources": [] if sources is None else sources,
        }
    )
    return converter.convert(markdown, _REPO_ROOT)


def _structural_sources(output: str) -> int:
    return output.count('[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]')


def test_config_sources_emitted_once_without_note_section():
    module = _load_converter_module()
    output = _convert(module, "# Введение\n\nТекст.\n", CONFIG_SOURCES)

    assert _structural_sources(output) == 1
    assert output.count("[SOURCE number=") == 2
    assert "Источник из конфига А" in output


def test_note_sources_win_over_config_sources():
    module = _load_converter_module()
    markdown = (
        "# Введение\n\nТекст.\n\n"
        "# СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\n\n"
        "1. Первый источник из заметки.\n"
        "2. Второй источник из заметки.\n"
    )

    output = _convert(module, markdown, CONFIG_SOURCES)

    assert _structural_sources(output) == 1
    sources = [line for line in output.splitlines() if line.startswith("[SOURCE")]
    assert sources == [
        "[SOURCE number=1] Первый источник из заметки.",
        "[SOURCE number=2] Второй источник из заметки.",
    ]
    assert "Источник из конфига" not in output
    assert "[LIST type=numbered]" not in output


def test_note_sources_alias_heading_and_bullets():
    module = _load_converter_module()
    markdown = "# СПИСОК ЛИТЕРАТУРЫ\n\n- Источник через дефис.\n"

    output = _convert(module, markdown, CONFIG_SOURCES)

    assert _structural_sources(output) == 1
    assert "[SOURCE number=1] Источник через дефис." in output
    assert "Источник из конфига" not in output


def test_note_sources_not_repeated_after_appendix():
    module = _load_converter_module()
    markdown = (
        "# Введение\n\nТекст.\n\n"
        "# СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\n\n"
        "1. Источник из заметки.\n\n"
        "# Приложение 1\n\n[Текст]\n"
    )

    output = _convert(module, markdown, CONFIG_SOURCES)

    assert _structural_sources(output) == 1
    assert output.count("[SOURCE number=") == 1
    assert "[APPENDIX" in output
    assert "Источник из конфига" not in output


def test_figures_and_tables_inside_note_sources_still_convert():
    module = _load_converter_module()
    markdown = (
        "# СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\n\n1. Первый источник.\n\n| Ключ | Значение |\n| --- | --- |\n| a | b |\n"
    )

    output = _convert(module, markdown, [])

    assert "[SOURCE number=1] Первый источник." in output
    assert "[TABLE]" in output


def test_empty_note_sources_section_filled_from_config():
    module = _load_converter_module()
    markdown = "# Введение\n\nТекст.\n\n# СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\n"

    output = _convert(module, markdown, CONFIG_SOURCES)

    assert _structural_sources(output) == 1
    assert output.count("[SOURCE number=") == 2
    assert "Источник из конфига А" in output
