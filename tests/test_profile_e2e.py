from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from docx import Document

from sfu_converter import cli
from sfu_converter.domain.diagnostics import DiagnosticCodes
from sfu_converter.infrastructure.docx_inspector import dump


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "profiles"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIGURE_SRC_RE = re.compile(r'\[FIGURE[^\]]*\bsrc="([^"]+)"')
PROFILE_NAMES = (
    "coursework",
    "graduation_qualification_work",
    "practice_reports",
    "research_reports",
    "lab_practical_project_reports",
    "small_written_works",
    "graphic_and_demonstration_materials",
    "project_designations",
    "common",
)
BASELINE_VALIDATOR_WARNING_CODES = {DiagnosticCodes.FORMAT_RULE_NOT_SUPPORTED}


def test_profile_fixture_figure_assets_exist():
    missing = []
    for input_path in FIXTURE_ROOT.glob("*/input.txt"):
        source = input_path.read_text(encoding="utf-8")
        for image_name in FIGURE_SRC_RE.findall(source):
            if Path(image_name).is_absolute():
                continue
            image_path = PROJECT_ROOT / "images" / image_name
            if not image_path.is_file():
                missing.append(f"{input_path.parent.name}: {image_name}")

    assert missing == []


@pytest.mark.e2e
@pytest.mark.parametrize("profile_name", PROFILE_NAMES)
def test_profile_fixture_round_trips(profile_name, tmp_path, capsys, request):
    fixture_dir = FIXTURE_ROOT / profile_name
    input_path = fixture_dir / "input.txt"
    output_path = tmp_path / f"{profile_name}.docx"

    exit_code = cli.main(
        [
            "--format",
            "json",
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--profile",
            profile_name,
            "--syntax-version",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    diagnostics = _canonical_diagnostics(payload["diagnostics"])
    first_page = dump(Document(str(output_path)), stop_at_page_break=True)

    if request.config.getoption("--update-fixtures"):
        _write_json(fixture_dir / "expected_diagnostics.json", diagnostics)
        (fixture_dir / "expected_first_page.txt").write_text(first_page, encoding="utf-8")

    assert exit_code == cli.ExitCodes.SUCCESS
    assert output_path.exists()
    assert diagnostics == _read_json(fixture_dir / "expected_diagnostics.json")
    assert first_page == (fixture_dir / "expected_first_page.txt").read_text(encoding="utf-8")

    validate_exit = cli.main(
        [
            "--format",
            "json",
            "validate-docx",
            "--input",
            str(output_path),
            "--profile",
            profile_name,
        ]
    )
    validate_payload = json.loads(capsys.readouterr().out)
    actionable = [
        diagnostic
        for diagnostic in validate_payload["diagnostics"]
        if diagnostic["code"] not in BASELINE_VALIDATOR_WARNING_CODES
    ]

    assert validate_exit == cli.ExitCodes.SUCCESS
    assert all(diagnostic["severity"] == "info" for diagnostic in actionable)


@pytest.mark.e2e
def test_profile_fixture_missing_required_metadata_changes_diagnostics(tmp_path, capsys):
    source = (FIXTURE_ROOT / "coursework" / "input.txt").read_text(encoding="utf-8")
    broken_input = tmp_path / "missing-student.txt"
    broken_input.write_text(
        "\n".join(
            line
            for line in source.splitlines()
            if 'key=student ' not in line
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "missing-student.docx"

    exit_code = cli.main(
        [
            "--format",
            "json",
            "convert",
            "--input",
            str(broken_input),
            "--output",
            str(output_path),
            "--profile",
            "coursework",
            "--syntax-version",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    diagnostics = _canonical_diagnostics(payload["diagnostics"])
    baseline = _read_json(FIXTURE_ROOT / "coursework" / "expected_diagnostics.json")
    new_diagnostics = [diagnostic for diagnostic in diagnostics if diagnostic not in baseline]

    assert exit_code == cli.ExitCodes.SUCCESS
    assert any(
        diagnostic["code"] == DiagnosticCodes.TXT_MISSING_METADATA
        and diagnostic["ruleId"] in {"coursework.title_page.form_i", "form_i"}
        and ("student" in diagnostic["message"] or diagnostic["data"].get("field") == "student")
        for diagnostic in new_diagnostics
    )


def _canonical_diagnostics(diagnostics: list[dict[str, object]]) -> list[dict[str, object]]:
    return [_canonical_diagnostic(diagnostic) for diagnostic in diagnostics]


def _canonical_diagnostic(diagnostic: dict[str, object]) -> dict[str, object]:
    source = dict(diagnostic.get("source") or {})
    document = source.get("document")
    if isinstance(document, str) and document.endswith("input.txt"):
        source["document"] = "input.txt"
    return {
        "code": diagnostic["code"],
        "severity": diagnostic["severity"],
        "message": diagnostic["message"],
        "ruleId": diagnostic.get("ruleId"),
        "source": source,
        "data": diagnostic.get("data") or {},
        **({"target": diagnostic["target"]} if "target" in diagnostic else {}),
    }


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
