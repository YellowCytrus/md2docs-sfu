"""Bold markup from Markdown tables must survive into the DOCX."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"


def _load_converter_module():
    spec = importlib.util.spec_from_file_location("obsidian2sfu_tables_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _convert(markdown: str) -> str:
    module = _load_converter_module()
    converter = module.MarkdownConverter(
        {
            "meta": {"profile": "lab_practical_project_reports"},
            "meta_items": [],
            "sources": [],
        }
    )
    return converter.convert(markdown, _REPO_ROOT)


def _table_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("|")]


def test_bold_in_table_cells_is_kept():
    output = _convert("| Параметр | Комментарий |\n| --- | --- |\n| Давление | **критично** при нагреве |\n")

    assert _table_lines(output)[1] == "| Давление | **критично** при нагреве |"


def test_underscore_bold_in_table_cells_becomes_asterisks():
    output = _convert("| Параметр | Комментарий |\n| --- | --- |\n| Температура | __горячо__ |\n")

    assert _table_lines(output)[1] == "| Температура | **горячо** |"


def test_italics_and_code_spans_in_cells_stay_plain():
    output = _convert("| Параметр | Комментарий |\n| --- | --- |\n| Ссылка | `code` и *курсив* |\n")

    assert _table_lines(output)[1] == "| Ссылка | code и курсив |"


def test_bold_is_dropped_from_list_items():
    """Lists remain plain text in V2, so their markers must not leak."""
    output = _convert("- **первый** пункт\n")

    assert "[1)]" in output or "[-]" in output
    assert "**" not in output
