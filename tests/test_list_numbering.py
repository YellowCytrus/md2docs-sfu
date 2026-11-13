"""Every numbered list block must restart Word's counter at "1."."""

from docx import Document as DocxDocument
from docx.oxml.ns import qn

from sfu_converter.domain.ast_nodes import Document, ListItemNode, ListNode, ListType
from sfu_converter.infrastructure.docx_renderer import DocxRenderer
from sfu_converter.registry.loader import get_profile


def _render(tmp_path, blocks, name="lists.docx"):
    renderer = DocxRenderer(base_dir=tmp_path)
    output_path = tmp_path / name
    renderer.render_to_file(Document(blocks=tuple(blocks)), get_profile("common"), str(output_path))
    return DocxDocument(str(output_path))


def _list_items(doc):
    """Return ``(numId, text)`` for every paragraph with Word list numbering."""
    items = []
    for paragraph in doc.paragraphs:
        p_pr = paragraph._p.pPr
        if p_pr is not None and p_pr.numPr is not None:
            items.append((int(p_pr.numPr.numId.val), paragraph.text))
    return items


def _num(doc, num_id):
    numbering = doc.part.numbering_part.element
    for num in numbering.findall(qn("w:num")):
        if int(num.get(qn("w:numId"))) == num_id:
            return num
    raise AssertionError(f"numId {num_id} is not defined in numbering.xml")


def _abstract_id(num) -> int:
    return int(num.find(qn("w:abstractNumId")).get(qn("w:val")))


def _start_overrides(num) -> dict[int, int]:
    return {
        int(override.get(qn("w:ilvl"))): int(override.find(qn("w:startOverride")).get(qn("w:val")))
        for override in num.findall(qn("w:lvlOverride"))
    }


def test_each_numbered_list_restarts_at_one(tmp_path):
    doc = _render(
        tmp_path,
        [
            ListNode(
                list_type=ListType.NUMBERED,
                items=(ListItemNode("первый пункт"), ListItemNode("второй пункт")),
            ),
            ListNode(
                list_type=ListType.NUMBERED,
                items=(ListItemNode("третий пункт"), ListItemNode("четвёртый пункт")),
            ),
        ],
    )

    items = _list_items(doc)
    assert [text for _, text in items] == [
        "первый пункт;",
        "второй пункт.",
        "третий пункт;",
        "четвёртый пункт.",
    ]

    first_list = items[0][0]
    second_list = items[2][0]
    assert items[0][0] == items[1][0], "items of one list share a counter"
    assert items[2][0] == items[3][0], "items of one list share a counter"
    assert first_list != second_list, "adjacent lists must not share a counter"

    first_num = _num(doc, first_list)
    second_num = _num(doc, second_list)
    assert _abstract_id(first_num) == _abstract_id(second_num), "same list look, different counters"
    assert _start_overrides(first_num) == {0: 1, 1: 1, 2: 1}
    assert _start_overrides(second_num) == {0: 1, 1: 1, 2: 1}


def test_nested_numbered_list_restarts_in_every_parent_item(tmp_path):
    doc = _render(
        tmp_path,
        [
            ListNode(
                list_type=ListType.NUMBERED,
                items=(
                    ListItemNode(
                        "первый пункт",
                        children=(
                            ListNode(
                                list_type=ListType.NUMBERED,
                                items=(ListItemNode("вложенный раз"), ListItemNode("вложенный два")),
                            ),
                        ),
                    ),
                    ListItemNode(
                        "второй пункт",
                        children=(
                            ListNode(
                                list_type=ListType.NUMBERED,
                                items=(ListItemNode("вложенный три"),),
                            ),
                        ),
                    ),
                ),
            ),
        ],
    )

    numbered = _list_items(doc)
    assert [text for _, text in numbered] == [
        "первый пункт;",
        "вложенный раз;",
        "вложенный два.",
        "второй пункт.",
        "вложенный три.",
    ]
    assert numbered[3][0] == numbered[0][0], "outer items share a counter"
    assert numbered[1][0] == numbered[2][0], "nested items share a counter"
    assert numbered[1][0] != numbered[4][0], "each nested list owns its counter"


def test_bullet_lists_keep_sharing_one_definition(tmp_path):
    doc = _render(
        tmp_path,
        [
            ListNode(list_type=ListType.BULLET, items=(ListItemNode("первый"),)),
            ListNode(list_type=ListType.BULLET, items=(ListItemNode("второй"),)),
        ],
    )

    items = _list_items(doc)
    assert [num_id for num_id, _ in items] == [items[0][0], items[0][0]]
    assert _start_overrides(_num(doc, items[0][0])) == {}
