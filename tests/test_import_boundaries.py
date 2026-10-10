import ast
from pathlib import Path


def test_application_and_domain_do_not_import_python_docx():
    root = Path(__file__).resolve().parents[1] / "src" / "sfu_converter"
    checked_files = [
        *sorted((root / "application").glob("*.py")),
        *sorted((root / "domain").glob("*.py")),
    ]

    offenders = []
    for path in checked_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "docx" or alias.name.startswith("docx."):
                        offenders.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "docx" or (node.module or "").startswith("docx."):
                    offenders.append(f"{path}: from {node.module} import ...")

    assert offenders == []
