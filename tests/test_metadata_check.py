from sfu_converter.application.metadata_check import run
from sfu_converter.domain.ast_nodes import Document
from sfu_converter.domain.diagnostics import DiagnosticCodes, Severity
from sfu_converter.registry import get_profile


def _missing_for(document, profile_name):
    return [
        diagnostic
        for diagnostic in run(document, get_profile(profile_name))
        if diagnostic.code == DiagnosticCodes.TXT_MISSING_METADATA
    ]


def test_coursework_missing_supervisor_reports_metadata_diagnostic():
    document = Document(
        blocks=(),
        metadata={"title": "Работа", "student": "Иванов И.И.", "group": "КИ20-01"},
    )

    diagnostics = _missing_for(document, "coursework")

    diagnostic = next(d for d in diagnostics if d.rule_id == "coursework.metadata.required")
    assert diagnostic.severity is Severity.WARNING
    assert diagnostic.data == {
        "profile": "coursework",
        "missing": ["supervisor"],
        "ruleId": "coursework.metadata.required",
    }


def test_vkr_form_b_missing_direction_code_uses_selected_title_page_rule():
    document = Document(
        blocks=(),
        metadata={
            "title": "ВКР",
            "student": "Иванов И.И.",
            "supervisor": "Петров П.П.",
            "direction_name": "Информатика",
            "master_program_code": "09.04.01",
            "master_program_name": "Разработка ПО",
            "reviewer": "Сидоров С.С.",
        },
    )

    diagnostics = _missing_for(document, "graduation_qualification_work")

    diagnostic = next(
        d for d in diagnostics if d.rule_id == "graduation_qualification_work.title_page.form_b"
    )
    assert diagnostic.data["missing"] == ["direction_code"]
    assert diagnostic.data["ruleId"] == "graduation_qualification_work.title_page.form_b"


def test_metadata_check_accepts_complete_coursework_metadata():
    document = Document(
        blocks=(),
        metadata={
            "title": "Работа",
            "student": "Иванов И.И.",
            "group": "КИ20-01",
            "supervisor": "Петров П.П.",
        },
    )

    assert _missing_for(document, "coursework") == []
