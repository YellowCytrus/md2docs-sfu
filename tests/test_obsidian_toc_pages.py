"""Page-number assignment for the obsidian2sfu table of contents."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_obsidian2sfu():
    spec = importlib.util.spec_from_file_location(
        "obsidian2sfu_toc_module", REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PAGES = [
    "Титульный лист",
    "СОДЕРЖАНИЕ\n"
    "1 Цель работы................................................ 2\n"
    "2 Постановка задачи......................................... 2\n"
    "3 Теоретические сведения.................................... 2",
    "1 Цель работы\n\nИзучение метода.",
    "2 Постановка задачи\n\nДан граф.",
    "3 Теоретические сведения\n\nОриентированный граф.",
]


def test_body_start_skips_title_and_toc_pages():
    module = _load_obsidian2sfu()

    assert module._body_start_page(PAGES) == 3


def test_assign_pages_does_not_match_headings_in_the_toc_itself():
    module = _load_obsidian2sfu()
    entries = [
        SimpleNamespace(text="1 Цель работы\t2"),
        SimpleNamespace(text="2 Постановка задачи\t2"),
        SimpleNamespace(text="3 Теоретические сведения\t2"),
    ]

    mapping = module.assign_pages(entries, PAGES)

    assert mapping == {
        "1 Цель работы\t2": 3,
        "2 Постановка задачи\t2": 4,
        "3 Теоретические сведения\t2": 5,
    }


def test_set_toc_entry_page_rewrites_split_runs_without_duplicating_heading():
    module = _load_obsidian2sfu()
    from docx import Document

    doc = Document()
    paragraph = doc.add_paragraph()
    paragraph.add_run("4.1 Анализ графа ")
    paragraph.add_run("\t2")

    module.set_toc_entry_page(paragraph, 6)

    assert paragraph.text == "4.1 Анализ графа\t6"
    assert len(paragraph.runs) == 1
