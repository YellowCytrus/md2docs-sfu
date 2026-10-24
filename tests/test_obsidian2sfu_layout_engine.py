"""Cross-platform discovery of the LibreOffice layout engine.

Table splitting (and therefore the "Продолжение/Окончание таблицы" captions)
only happens when ``obsidian2sfu`` can reach LibreOffice over UNO. On Windows
neither the binary nor pyuno is on ``PATH``: ``soffice.exe`` lives in the
install directory and the bindings live in LibreOffice's bundled interpreter.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "obsidian2sfu" / "obsidian2sfu.py"


def _load_converter_module():
    spec = importlib.util.spec_from_file_location("obsidian2sfu_layout_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _WindowsOS:
    """Stand-in for ``os`` on Windows without changing the real ``os.name``.

    ``pathlib`` picks its flavour from ``os.name`` while a ``Path`` is created,
    so patching the real module would break path handling inside the test.
    """

    name = "nt"

    def __init__(self):
        self.environ = os.environ


def test_find_libreoffice_uses_windows_install_dir(monkeypatch, tmp_path):
    module = _load_converter_module()
    soffice = tmp_path / "LibreOffice" / "program" / "soffice.exe"
    soffice.parent.mkdir(parents=True)
    soffice.write_text("", encoding="utf-8")

    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(module, "os", _WindowsOS())
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert module._find_libreoffice() == str(soffice)


def test_uno_python_prefers_libreoffice_bundled_interpreter(monkeypatch, tmp_path):
    module = _load_converter_module()
    program = tmp_path / "LibreOffice" / "program"
    program.mkdir(parents=True)
    soffice = program / "soffice.exe"
    soffice.write_text("", encoding="utf-8")
    bundled_python = program / "python.exe"
    bundled_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(module, "os", _WindowsOS())
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: type("Probe", (), {"returncode": 0})(),
    )

    assert module._uno_python(str(soffice)) == str(bundled_python)


def test_layout_is_skipped_when_no_python_can_import_uno(monkeypatch, tmp_path):
    module = _load_converter_module()
    monkeypatch.setattr(module, "_find_libreoffice", lambda: "/usr/bin/soffice")
    monkeypatch.setattr(module, "_uno_module", lambda: None)
    monkeypatch.setattr(module, "_uno_python", lambda soffice: None)

    assert module._layout_table_pages(tmp_path / "doc.docx", 2100) is None


def test_find_libreoffice_prefers_path_lookup(monkeypatch):
    module = _load_converter_module()
    monkeypatch.setattr(module.shutil, "which", lambda name: "/opt/soffice" if name == "soffice" else None)

    assert module._find_libreoffice() == "/opt/soffice"


