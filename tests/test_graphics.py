from sfu_converter.domain.ast_nodes import (
    Document,
    DrawingSheetNode,
    PosterNode,
    SheetFormat,
    SlideDeckNode,
    SlideNode,
)
from sfu_converter.infrastructure.graphics import validate
from sfu_converter.parser import V2Parser
from sfu_converter.registry import get_profile


def _codes(document: Document) -> set[str]:
    return {diagnostic.rule_id for diagnostic in validate(document, get_profile("graphic_and_demonstration_materials"))}


def test_v2_parser_parses_graphic_material_nodes():
    result = V2Parser().parse(
        "\n".join(
            [
                '[DRAWING sheet=A1 frame=graphic form=form_5 scale="1:50"]',
                'src="diagram.svg"',
                "designation=ДП-23.05.02 ABCDEF.001 Э3",
                "[/DRAWING]",
                '[POSTER format=A1 title="Архитектура системы" fill=75]',
                "[P] Материалы плаката",
                "[/POSTER]",
                "[SLIDE_DECK format=A4]",
                '[SLIDE first_slide=true title="Тема" student="Иванов" supervisor="Петров"]',
                'university="СФУ"',
                'institute="ИКИТ"',
                'city="Красноярск"',
                "year=2026",
                "[/SLIDE]",
                '[SLIDE title="Тема"][/SLIDE]',
                "[/SLIDE_DECK]",
            ]
        )
    )

    assert result.diagnostics == []
    drawing, poster, deck = result.document.blocks
    assert isinstance(drawing, DrawingSheetNode)
    assert drawing.sheet_format is SheetFormat.A1
    assert drawing.scale == "1:50"
    assert drawing.src == "diagram.svg"
    assert isinstance(poster, PosterNode)
    assert poster.fill_percent == 75
    assert isinstance(deck, SlideDeckNode)
    assert len(deck.slides) == 2
    assert deck.slides[0].fields["supervisor"] == "Петров"


def test_drawing_scale_not_in_gost_set_is_reported():
    document = Document(
        blocks=(
            DrawingSheetNode(
                sheet_format=SheetFormat.A1,
                scale="1:1000",
                src="diagram.svg",
            ),
        )
    )

    assert "graphic_and_demonstration_materials.drawing.scale_set" in _codes(document)


def test_poster_low_fill_density_is_reported():
    document = Document(
        blocks=(PosterNode(sheet_format=SheetFormat.A1, title="Архитектура", fill_percent=30),)
    )

    assert "graphic_and_demonstration_materials.poster.fill_density" in _codes(document)


def test_slide_deck_missing_first_slide_field_is_reported():
    document = Document(
        blocks=(
            SlideDeckNode(
                slides=(
                    SlideNode(
                        first_slide=True,
                        fields={
                            "university": "СФУ",
                            "institute": "ИКИТ",
                            "title": "Тема",
                            "student": "Иванов",
                            "city": "Красноярск",
                            "year": "2026",
                        },
                    ),
                )
            ),
        )
    )

    assert "graphic_and_demonstration_materials.slide.required_first_slide_fields" in _codes(document)


def test_slide_deck_mismatched_titles_are_reported():
    document = Document(
        blocks=(
            SlideDeckNode(
                slides=(
                    SlideNode(first_slide=True, fields={"title": "Цель"}),
                    SlideNode(fields={"title": "Методы"}),
                )
            ),
        )
    )

    assert "graphic_and_demonstration_materials.slide.header_continuity" in _codes(document)
