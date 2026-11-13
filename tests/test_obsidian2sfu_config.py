"""Numbered list marker option in the obsidian2sfu config."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"


def _load_converter_module():
    spec = importlib.util.spec_from_file_location("obsidian2sfu_config_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _note(tmp_path: Path) -> Path:
    note = tmp_path / "note.md"
    note.write_text("# Заметка\n\nТекст.\n", encoding="utf-8")
    return note


def test_load_config_defaults_to_dot_marker(tmp_path, monkeypatch):
    module = _load_converter_module()
    monkeypatch.setattr(module, "DEFAULT_CONFIG", tmp_path / "missing.json")

    cfg = module.load_config(_note(tmp_path), {})

    assert cfg["numbered_list_marker"] == "dot"


def test_load_config_reads_numbered_list_marker(tmp_path, monkeypatch):
    module = _load_converter_module()
    monkeypatch.setattr(module, "DEFAULT_CONFIG", tmp_path / "missing.json")
    config = tmp_path / "report.json"
    config.write_text(json.dumps({"numbered_list_marker": "paren"}), encoding="utf-8")

    cfg = module.load_config(_note(tmp_path), {}, str(config))

    assert cfg["numbered_list_marker"] == "paren"


def test_run_converter_passes_numbered_list_marker(tmp_path, monkeypatch):
    module = _load_converter_module()
    commands = []

    def fake_run(cmd, check=False):
        commands.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_converter(
        "sfu-converter",
        tmp_path / "note.txt",
        tmp_path / "note.docx",
        "lab_practical_project_reports",
        tmp_path,
        "paren",
    )

    command = commands[0]
    index = command.index("--numbered-list-marker")
    assert command[index + 1] == "paren"
