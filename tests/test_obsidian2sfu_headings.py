"""Regression tests for markdown-to-SFU heading level conversion.

# rule: common.heading.h5
# rule: common.heading.h6
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"


def _load_converter_module():
    spec = importlib.util.spec_from_file_location("obsidian2sfu_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_markdown_headings_keep_levels_up_to_six():
    module = _load_converter_module()
    converter = module.MarkdownConverter({"meta": {"profile": "common"}, "meta_items": []})
    markdown = "\n\n".join(f"{'#' * level} Heading {level}" for level in range(2, 7))

    output = converter.convert(markdown, _REPO_ROOT)

    for level in range(2, 7):
        assert f'[H level={level} title="Heading {level}"' in output
