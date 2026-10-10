from __future__ import annotations

from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes"


def add_footnote_reference(run, footnote_id: int) -> None:
    reference = OxmlElement("w:footnoteReference")
    reference.set(qn("w:id"), str(footnote_id))
    run._element.append(reference)
    run.font.superscript = True


def patch_docx_bytes(docx_bytes: bytes, footnotes: dict[int, str]) -> bytes:
    if not footnotes:
        return docx_bytes

    source = BytesIO(docx_bytes)
    destination = BytesIO()
    replacements = {
        "[Content_Types].xml": _patch_content_types,
        "word/_rels/document.xml.rels": _patch_document_rels,
    }

    with ZipFile(source, "r") as src, ZipFile(destination, "w", ZIP_DEFLATED) as dst:
        written = set()
        for item in src.infolist():
            data = src.read(item.filename)
            patch = replacements.get(item.filename)
            if patch is not None:
                data = patch(data)
            if item.filename == "word/footnotes.xml":
                data = _footnotes_xml(footnotes).encode("utf-8")
            dst.writestr(item, data)
            written.add(item.filename)

        if "word/footnotes.xml" not in written:
            dst.writestr("word/footnotes.xml", _footnotes_xml(footnotes).encode("utf-8"))
        if "word/_rels/document.xml.rels" not in written:
            dst.writestr("word/_rels/document.xml.rels", _new_document_rels().encode("utf-8"))

    return destination.getvalue()


def patch_docx_file(path, footnotes: dict[int, str]) -> None:
    if not footnotes:
        return
    path.write_bytes(patch_docx_bytes(path.read_bytes(), footnotes))


def _patch_content_types(data: bytes) -> bytes:
    xml = data.decode("utf-8")
    if "footnotes+xml" in xml:
        return data
    override = (
        '<Override PartName="/word/footnotes.xml" '
        f'ContentType="{_CONTENT_TYPE}"/>'
    )
    return xml.replace("</Types>", f"{override}</Types>").encode("utf-8")


def _patch_document_rels(data: bytes) -> bytes:
    xml = data.decode("utf-8")
    if _REL_TYPE in xml:
        return data
    rel_id = _next_rel_id(xml)
    relationship = f'<Relationship Id="{rel_id}" Type="{_REL_TYPE}" Target="footnotes.xml"/>'
    return xml.replace("</Relationships>", f"{relationship}</Relationships>").encode("utf-8")


def _new_document_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{_REL_TYPE}" Target="footnotes.xml"/>'
        "</Relationships>"
    )


def _next_rel_id(xml: str) -> str:
    index = 1
    while f'Id="rId{index}"' in xml:
        index += 1
    return f"rId{index}"


def _footnotes_xml(footnotes: dict[int, str]) -> str:
    notes = "".join(_footnote_xml(note_id, text) for note_id, text in sorted(footnotes.items()))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
        f"{notes}</w:footnotes>"
    )


def _footnote_xml(note_id: int, text: str) -> str:
    body = escape(text)
    return (
        f'<w:footnote w:id="{note_id}">'
        '<w:p>'
        '<w:pPr><w:spacing w:line="240" w:lineRule="auto"/><w:pStyle w:val="SFUFootnoteText"/></w:pPr>'
        '<w:r><w:rPr><w:vertAlign w:val="superscript"/><w:sz w:val="24"/></w:rPr>'
        '<w:footnoteRef/></w:r>'
        f'<w:r><w:rPr><w:vertAlign w:val="superscript"/><w:sz w:val="24"/></w:rPr><w:t>{note_id}</w:t></w:r>'
        '<w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r>'
        f'<w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t>{body}</w:t></w:r>'
        '</w:p>'
        '</w:footnote>'
    )
