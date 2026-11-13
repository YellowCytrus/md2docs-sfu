"""Real Word list numbering for bulleted/numbered lists.

Instead of writing the marker as literal text ("- ", "1.") the renderer paints
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
_TWIPS_PER_CM = 566.929133858

_BULLET_MARKERS = ("\u2013", "\u2013", "\u2013")  # en dash at every level
_NUMBER_FORMATS = ("decimal", "lowerLetter", "decimal")

#: Numbered list marker styles. ``dot`` gives "1.", ``paren`` gives "1)".
NUMBERED_MARKER_DOT = "dot"
NUMBERED_MARKER_PAREN = "paren"
NUMBERED_MARKERS = (NUMBERED_MARKER_DOT, NUMBERED_MARKER_PAREN)
DEFAULT_NUMBERED_MARKER = NUMBERED_MARKER_DOT

# Level 0 is the list counter itself; deeper levels are lettered/nested numeric
# lists and always keep the closing parenthesis ("а)", "1)").
_NUMBER_TEXTS = {
    NUMBERED_MARKER_DOT: ("%1.", "%2)", "%3)"),
    NUMBERED_MARKER_PAREN: ("%1)", "%2)", "%3)"),
}


def _twips(cm: float) -> str:
    return str(int(round(cm * _TWIPS_PER_CM)))


def _lvl_xml(kind: str, ilvl: int, marker: str = DEFAULT_NUMBERED_MARKER) -> str:
    # "bibliography" is only a separate counter (see apply_word_bibliography);
    # its levels are painted exactly like a regular numbered list.
    if kind == "bullet":
        num_fmt = "bullet"
        lvl_text = _BULLET_MARKERS[min(ilvl, len(_BULLET_MARKERS) - 1)]
        rpr = (
            '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
            ' w:cs="Times New Roman"/></w:rPr>'
        )
    else:
        num_fmt = _NUMBER_FORMATS[ilvl]
        lvl_text = _NUMBER_TEXTS[marker][ilvl]
        rpr = ""
    left = ilvl * _LIST_LEVEL_STEP_CM
    ind = f'<w:ind w:left="{_twips(left)}" w:firstLine="{_twips(_LIST_FIRST_LINE_CM)}"/>'
    # A single space after the marker (instead of Word's tab) keeps the
    # marker-to-text gap small.
    return (
        f'<w:lvl w:ilvl="{ilvl}">'
        '<w:start w:val="1"/>'
        f'<w:numFmt w:val="{num_fmt}"/>'
        '<w:suff w:val="space"/>'
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


def ensure_list_numbering(document, list_type: ListType, *, marker: str = DEFAULT_NUMBERED_MARKER) -> int:
    """Return the shared ``numId`` for the list type, creating it on first use.

    Every call returns the same ``numId``, so the counter keeps running across
    the paragraphs. Use :func:`start_list_numbering` once per list block to get
    a counter that restarts at 1.
    """
    kind = "bullet" if list_type is ListType.BULLET else "number"
    return _ensure_kind(document, kind, marker=marker)


def start_list_numbering(document, list_type: ListType, *, marker: str = DEFAULT_NUMBERED_MARKER) -> int:
    """Return the ``numId`` of one list block, restarting its counter at 1.

    Each numbered list must own a separate ``w:num`` instance: sharing one
    ``numId`` makes Word continue "1., 2., … 17." across unrelated lists.
    Bullets carry no counter, so they keep sharing a single definition.
    """
    kind = "bullet" if list_type is ListType.BULLET else "number"
    if kind == "bullet":
        return _ensure_kind(document, kind, marker=marker)
    return _new_counter(document, kind, marker=marker)


def _cache(document) -> dict:
    cache = getattr(document, _CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(document, _CACHE_ATTR, cache)
    return cache


def _cache_key(kind: str, marker: str) -> tuple[str, ...]:
    return (kind, marker) if kind == "number" else (kind,)


def _ensure_kind(document, kind: str, *, marker: str = DEFAULT_NUMBERED_MARKER) -> int:
    """Create the abstract definition of ``kind`` once and reuse its ``numId``."""
    _, num_id = _ensure_abstract(document, kind, marker=marker)
    return num_id


def _ensure_abstract(document, kind: str, *, marker: str = DEFAULT_NUMBERED_MARKER) -> tuple[int, int]:
    if kind == "number" and marker not in _NUMBER_TEXTS:
        raise ValueError(f"Unknown numbered list marker: {marker!r}")
    cache = _cache(document)
    cache_key = _cache_key(kind, marker)
    if cache_key in cache:
        return cache[cache_key]

    numbering = document.part.numbering_part.element
    abstract_id, num_id = _next_ids(numbering)

    levels = "".join(_lvl_xml(kind, ilvl, marker) for ilvl in range(3))
    abstract = parse_xml(
        f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">'
        '<w:multiLevelType w:val="hybridMultilevel"/>'
        f"{levels}"
        "</w:abstractNum>"
    )
    numbering.insert(0, abstract)
    _append_num(numbering, _num_element(num_id, abstract_id))

    cache[cache_key] = (abstract_id, num_id)
    return abstract_id, num_id


def _new_counter(document, kind: str, *, marker: str) -> int:
    """Append a ``w:num`` that restarts the shared abstract list at 1."""
    abstract_id, _ = _ensure_abstract(document, kind, marker=marker)
    numbering = document.part.numbering_part.element
    _, num_id = _next_ids(numbering)
    _append_num(numbering, _num_element(num_id, abstract_id, restart=True))
    return num_id


def _num_element(num_id: int, abstract_id: int, *, restart: bool = False):
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    ref = OxmlElement("w:abstractNumId")
    ref.set(qn("w:val"), str(abstract_id))
    num.append(ref)
    if restart:
        # Every level of this list starts from 1; a nested list ("а)") thus
        # restarts together with the list that contains it.
        for ilvl in range(3):
            override = OxmlElement("w:lvlOverride")
            override.set(qn("w:ilvl"), str(ilvl))
            start = OxmlElement("w:startOverride")
            start.set(qn("w:val"), "1")
            override.append(start)
            num.append(override)
    return num


def _append_num(numbering, num) -> None:
    cleanup = numbering.find(qn("w:numIdMacAtCleanup"))
    if cleanup is not None:
        cleanup.addprevious(num)
    else:
        numbering.append(num)


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


def apply_list_numbering(paragraph, num_id: int, *, level: int = 0) -> None:
    """Paint ``paragraph`` with the list counter ``num_id`` at ``level``."""
    _apply_numbering(paragraph, num_id, level=level)


def apply_word_list(
    paragraph,
    list_type: ListType,
    *,
    level: int = 0,
    document=None,
    marker: str = DEFAULT_NUMBERED_MARKER,
) -> None:
    if document is None:
        document = paragraph.part.document
    _apply_numbering(paragraph, ensure_list_numbering(document, list_type, marker=marker), level=level)


def apply_word_bibliography(paragraph, *, document=None) -> None:
    """Number a bibliography entry as a regular numbered list item.

    The entries look exactly like the body's numbered lists; the only
    difference is the counter, which starts at 1 so the source list is always
    numbered 1, 2, 3, … regardless of the lists before it.
    """
    if document is None:
        document = paragraph.part.document
    _apply_numbering(paragraph, _ensure_kind(document, "bibliography"), level=0)
