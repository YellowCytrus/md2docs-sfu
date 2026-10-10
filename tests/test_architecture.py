import ast
from pathlib import Path


def _imports_from(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_domain_layer_has_no_infrastructure_imports():
    root = Path(__file__).resolve().parents[1] / "src" / "sfu_converter" / "domain"
    forbidden = ("argparse", "docx", "sfu_converter.cli", "sfu_converter.infrastructure")
    offenders = []

    for path in sorted(root.glob("*.py")):
        for imported in _imports_from(path):
            if imported == "docx" or imported.startswith("docx."):
                offenders.append(f"{path.name} imports {imported}")
            elif imported in forbidden or imported.startswith("sfu_converter.infrastructure."):
                offenders.append(f"{path.name} imports {imported}")

    assert offenders == []


def test_application_layer_has_no_docx_imports():
    root = Path(__file__).resolve().parents[1] / "src" / "sfu_converter" / "application"
    offenders = []

    for path in sorted(root.glob("*.py")):
        for imported in _imports_from(path):
            if imported == "docx" or imported.startswith("docx."):
                offenders.append(f"{path.name} imports {imported}")

    assert offenders == []
