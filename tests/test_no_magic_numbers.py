from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "sfu_converter"
ALLOWED_RAW_CM_MODULES = {
    Path("domain/constants.py"),
    Path("infrastructure/section_setup.py"),
}


def test_raw_cm_numeric_literals_are_centralized():
    offenders: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        rel = path.relative_to(SOURCE_ROOT)
        if rel in ALLOWED_RAW_CM_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_cm_call(node):
                continue
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, int | float):
                offenders.append(f"{rel}:{node.lineno} uses Cm({node.args[0].value!r})")

    assert offenders == []


def _is_cm_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Name) and node.func.id == "Cm"
