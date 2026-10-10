from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from sfu_converter.domain.ast_nodes import Document, SlideDeckNode, SlideNode
from sfu_converter.domain.diagnostics import Diagnostic, Severity
from sfu_converter.domain.formatting import FormattingProfile


class PptxRenderer:
    """Render slide decks to PPTX without requiring the optional dependency at import time."""

    def render_to_file(
        self,
        document: Document,
        profile: FormattingProfile,
        output_path: str,
    ) -> list[Diagnostic]:
        deck = _first_deck(document)
        if deck is None:
            return [
                Diagnostic(
                    code="PPTX_SLIDE_DECK_MISSING",
                    message="PPTX output requires a SLIDE_DECK block",
                    severity=Severity.ERROR,
                )
            ]

        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pptx(deck, destination)
        return []


def _first_deck(document: Document) -> SlideDeckNode | None:
    for block in document.blocks:
        if isinstance(block, SlideDeckNode):
            return block
    return None


def _write_minimal_pptx(deck: SlideDeckNode, destination: Path) -> None:
    slides = deck.slides or (SlideNode(fields={"title": ""}),)
    with ZipFile(destination, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types(len(slides)))
        package.writestr("_rels/.rels", _root_relationships())
        package.writestr("ppt/presentation.xml", _presentation_xml(len(slides)))
        package.writestr("ppt/_rels/presentation.xml.rels", _presentation_relationships(len(slides)))
        for index, slide in enumerate(slides, start=1):
            package.writestr(f"ppt/slides/slide{index}.xml", _slide_xml(slide, index))


def _content_types(slide_count: int) -> str:
    overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  {overrides}
</Types>"""


def _root_relationships() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""


def _presentation_relationships(slide_count: int) -> str:
    relationships = "\n".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        f'Target="slides/slide{index}.xml"/>'
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {relationships}
</Relationships>"""


def _presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'<p:sldId id="{256 + index}" r:id="rId{index}"/>'
        for index in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>
    {slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="7200000" cy="10182000" type="custom"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""


def _slide_xml(slide: SlideNode, index: int) -> str:
    title = escape(str(slide.fields.get("title", f"Слайд {index}")))
    body_lines = [f"{key}: {value}" for key, value in slide.fields.items() if key != "title"]
    body_lines.extend(slide.body)
    body = escape("\n".join(body_lines))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      {_text_shape(2, "Title", title, 457200, 457200, 6286500, 914400)}
      {_text_shape(3, "Body", body, 457200, 1524000, 6286500, 7315200)}
    </p:spTree>
  </p:cSld>
</p:sld>"""


def _text_shape(shape_id: int, name: str, text: str, x: int, y: int, cx: int, cy: int) -> str:
    return f"""
      <p:sp>
        <p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>
        <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody>
      </p:sp>"""
