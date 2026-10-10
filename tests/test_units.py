from sfu_converter.application.units import validate_unit_consistency
from sfu_converter.domain.ast_nodes import Document, ParagraphNode, TextRun
from sfu_converter.domain.diagnostics import DiagnosticCodes


def test_unit_consistency_reports_different_units_for_same_quantity():
    document = Document(
        blocks=(
            ParagraphNode(
                runs=(TextRun("Масса образца составляет 5 кг, затем 200 г."),),
                metadata={"quantity": "mass"},
            ),
        )
    )

    diagnostics = validate_unit_consistency(document)

    diagnostic = next(
        item for item in diagnostics if item.code == DiagnosticCodes.STYLE_UNIT_INCONSISTENT
    )
    assert diagnostic.rule_id == "common.style.unit_consistency"
    assert diagnostic.data["quantity"] == "mass"
    assert diagnostic.data["units"] == ("кг", "г")
    assert len(diagnostic.data["spans"]) == 2
