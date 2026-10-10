from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Cm

from sfu_converter.domain.ast_nodes import (
    FrameType,
    SectionOrientation,
    SectionSetupNode,
    SheetFormat,
    TitleBlockForm,
)
from sfu_converter.infrastructure.frames import draw, has_frame
from sfu_converter.infrastructure.section_setup import configure


def assert_close(actual, expected) -> None:
    assert abs(actual - expected) < 1000


def test_section_setup_configures_a3_landscape_size_and_margins():
    doc = Document()
    node = SectionSetupNode(
        orientation=SectionOrientation.LANDSCAPE,
        sheet_format=SheetFormat.A3,
        frame=FrameType.TEXT_FOLLOWING,
        title_block_form=TitleBlockForm.FORM_3,
    )

    configure(doc, doc.sections[0], node)

    section = doc.sections[0]
    assert section.orientation == WD_ORIENT.LANDSCAPE
    assert_close(section.page_width, Cm(42))
    assert_close(section.page_height, Cm(29.7))
    assert_close(section.left_margin, Cm(2))
    assert_close(section.right_margin, Cm(2))
    assert_close(section.top_margin, Cm(3))
    assert_close(section.bottom_margin, Cm(1))


def test_frames_draws_page_border_at_standard_offsets():
    doc = Document()

    draw(doc, doc.sections[0])

    assert has_frame(doc)
    xml = doc.sections[0]._sectPr.xml
    assert "w:pgBorders" in xml
    assert 'w:offsetFrom="page"' in xml
