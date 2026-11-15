"""Tests for figure cross-references (``@tag``) in the markdown converter.

A note ends an image line with ``@tag`` and reuses the same ``@tag`` anywhere
in the text; the converter replaces the references with the figure number that
sfu-converter will assign ("1.1", "А.2", …) while leaving the illustration's
own tag out of the caption.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"
_IMAGE_DIR = Path(__file__).resolve().parent


def _load_converter_module():
    spec = importlib.util.spec_from_file_location("obsidian2sfu_refs_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _convert(markdown: str):
    module = _load_converter_module()
    converter = module.MarkdownConverter(
        {"meta": {"profile": "lab_practical_project_reports"}, "meta_items": []}
    )
    return converter, converter.convert(markdown, _IMAGE_DIR)


def test_tag_is_replaced_by_section_figure_number():
    converter, output = _convert(
        "# Введение\n\n"
        "Общая диаграмма представлена на рисунке @global.\n\n"
        "# Структуризация\n\n"
        "Повторно: рисунок @global.\n\n"
        "![Общая диаграмма](test_image.png)@global\n"
    )

    assert "на рисунке 1.1." in output
    assert "Повторно: рисунок 1.1." in output
    assert "id=fig:1" in output
    assert converter.unknown_refs == set()


def test_tag_on_image_line_does_not_leak_into_caption():
    _, output = _convert("![Общая диаграмма](test_image.png)@global\n")

    figure_line = next(line for line in output.splitlines() if line.startswith("[FIGURE"))
    assert 'caption="Общая диаграмма"' in figure_line
    assert "@global" not in figure_line
    assert "@global" not in output


def test_forward_reference_is_resolved():
    _, output = _convert("# Раздел\n\nСм. @second.\n\n![Вторая](test_image.png)@second\n")

    assert "См. 1.1." in output


def test_figure_before_first_section_uses_plain_number():
    _, output = _convert("См. @pic.\n\n![A](test_image.png)@pic\n")

    assert "См. 1." in output


def test_figures_restart_per_level_one_section():
    # The tags map to their own section numbers, not a global counter.
    _, output = _convert(
        "# Первый раздел\n\nСм. @a и @b.\n\n![A](test_image.png)@a\n\n"
        "# Второй раздел\n\n![B](test_image.png)@b\n"
    )
    assert "См. 1.1 и 2.1." in output


def test_appendix_figures_use_letter():
    _, output = _convert(
        "# Раздел\n\nСм. @b.\n\n"
        "## Приложение 1. Глоссарий\n\n"
        "![B](test_image.png)@b\n"
    )

    assert "См. А.1." in output


def test_references_work_in_lists_and_table_cells():
    _, output = _convert(
        "# Раздел\n\n"
        "- пункт @a\n\n"
        "| Ссылка | Значение |\n"
        "| --- | --- |\n"
        "| @a | 1 |\n\n"
        "![A](test_image.png)@a\n"
    )

    assert "[-] пункт 1.1" in output
    assert "| 1.1 | 1 |" in output


def test_unknown_tag_is_left_as_is_and_reported():
    converter, output = _convert("См. @missing.\n")

    assert "См. @missing." in output
    assert converter.unknown_refs == {"missing"}


def test_wikilink_image_supports_tag():
    _, output = _convert("![[test_image.png|Подпись]]@pic\n\nСм. @pic.\n")

    assert 'caption="Подпись"' in output
    assert "См. 1." in output
    assert "@pic" not in output
