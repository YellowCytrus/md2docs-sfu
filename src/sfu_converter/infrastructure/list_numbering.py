"""Real Word list numbering for bulleted/numbered lists.

Instead of writing the marker as literal text ("- ", "1)") the renderer paints
Word's own numbering, so the paragraphs are genuine structural list items that
renumber automatically when the document is edited.
"""

from __future__ import annotations

from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from sfu_converter.domain.ast_nodes import ListType

_CACHE_ATTR = "_sfu_list_numbering"
# Lists behave like a normal paragraph: the marker sits exactly on the red line
# (first-line indent) and continuation lines return to the left margin.
_LIST_FIRST_LINE_CM = 1.25
_LIST_LEVEL_STEP_CM = 1.25
# Bibliography keeps a hanging indent (number on the red line, text hangs).
_BIB_LEFT_CM = 1.85
_BIB_HANGING_CM = 0.6
_TWIPS_PER_CM = 566.929133858

_BULLET_MARKERS = ("\u2013", "\u2013", "\u2013")  # en dash at every level
_NUMBER_FORMATS = ("decimal", "lowerLetter", "decimal")
_NUMBER_TEXTS = ("%1)", "%2)", "%3)")
_BIBLIOGRAPHY_TEXTS = ("%1.", "%2.", "%3.")


def _twips(cm: float) -> str:
    return str(int(round(cm * _TWIPS_PER_CM)))


def _lvl_xml(kind: str, ilvl: int) -> str:
    if kind == "bibliography":
        ind = f'<w:ind w:left="{_twips(_BIB_LEFT_CM)}" w:hanging="{_twips(_BIB_HANGING_CM)}"/>'
    else:
        left = ilvl * _LIST_LEVEL_STEP_CM
        ind = f'<w:ind w:left="{_twips(left)}" w:firstLine="{_twips(_LIST_FIRST_LINE_CM)}"/>'
    if kind == "bibliography":
        num_fmt = "decimal"
        lvl_text = _BIBLIOGRAPHY_TEXTS[ilvl]
        rpr = ""
    elif kind == "number":
        num_fmt = _NUMBER_FORMATS[ilvl]
        lvl_text = _NUMBER_TEXTS[ilvl]
        rpr = ""
    else:
        num_fmt = "bullet"
        lvl_text = _BULLET_MARKERS[min(ilvl, len(_BULLET_MARKERS) - 1)]
        rpr = (
            '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
            ' w:cs="Times New Roman"/></w:rPr>'
        )
    # Lists: a single space after the marker (instead of Word's tab) keeps the
    # marker-to-text gap small. Bibliography keeps the tab so entries align.
    suff = "" if kind == "bibliography" else '<w:suff w:val="space"/>'
    return (
        f'<w:lvl w:ilvl="{ilvl}">'
        '<w:start w:val="1"/>'
        f'<w:numFmt w:val="{num_fmt}"/>'
        f"{suff}"
        f'<w:lvlText w:val="{lvl_text}"/>'
        '<w:lvlJc w:val="left"/>'
        f"<w:pPr>{ind}</w:pPr>"
        f"{rpr}"
        "</w:lvl>"
    )


def _next_ids(numbering):
    abstract_ids = [
        int(el.get(qn("w:abstractNumId")))
        for el in numbering.findall(qn("w:abstractNum"))
    ]
    num_ids = [int(el.get(qn("w:numId"))) for el in numbering.findall(qn("w:num"))]
    return max(abstract_ids, default=-1) + 1, max(num_ids, default=0) + 1


def ensure_list_numbering(document, list_type: ListType) -> int:
    """Return the ``numId`` for the list type, creating the definition on first use."""
    kind = "bullet" if list_type is ListType.BULLET else "number"
    return _ensure_kind(document, kind)


def _ensure_kind(document, kind: str) -> int:
    cache = getattr(document, _CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(document, _CACHE_ATTR, cache)
    if kind in cache:
        return cache[kind]

    numbering = document.part.numbering_part.element
    abstract_id, num_id = _next_ids(numbering)

    levels = "".join(_lvl_xml(kind, ilvl) for ilvl in range(3))
    abstract = parse_xml(
        f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">'
        '<w:multiLevelType w:val="hybridMultilevel"/>'
        f"{levels}"
        "</w:abstractNum>"
    )
    numbering.insert(0, abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    ref = OxmlElement("w:abstractNumId")
    ref.set(qn("w:val"), str(abstract_id))
    num.append(ref)
    cleanup = numbering.find(qn("w:numIdMacAtCleanup"))
    if cleanup is not None:
        cleanup.addprevious(num)
    else:
        numbering.append(num)

    cache[kind] = num_id
    return num_id


def _apply_numbering(paragraph, num_id: int, *, level: int = 0) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    existing = p_pr.find(qn("w:numPr"))
    if existing is not None:
        p_pr.remove(existing)
    num_pr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), str(min(level, 2)))
    num_ref = OxmlElement("w:numId")
    num_ref.set(qn("w:val"), str(num_id))
    num_pr.append(ilvl)
    num_pr.append(num_ref)
    p_pr.append(num_pr)

    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = None


def apply_word_list(paragraph, list_type: ListType, *, level: int = 0, document=None) -> None:
    if document is None:
        document = paragraph.part.document
    _apply_numbering(paragraph, ensure_list_numbering(document, list_type), level=level)


def apply_word_bibliography(paragraph, *, document=None) -> None:
    """Number a bibliography entry as a real Word list item (1., 2., …)."""
    if document is None:
        document = paragraph.part.document
    _apply_numbering(paragraph, _ensure_kind(document, "bibliography"), level=0)
