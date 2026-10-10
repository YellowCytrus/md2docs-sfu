import json

from sfu_converter import cli
from sfu_converter.parser.syntax_spec import get_syntax_spec


def test_v2_syntax_spec_lists_supported_blocks_from_metadata():
    spec = get_syntax_spec(2)

    block_names = [block["name"] for block in spec["blocks"]]
    assert spec["syntaxVersion"] == 2
    assert block_names == [
        "document",
        "metadata",
        "heading",
        "structural_section",
        "paragraph",
        "figure",
        "drawing",
        "poster",
        "slide_deck",
        "table",
        "list",
        "formula",
        "reference",
        "source",
        "footnote",
        "page_break",
        "appendix",
        "raw",
    ]
    assert spec["blocks"][2]["marker"] == '[H level=1 title="..." number=auto]'
    assert spec["blocks"][2]["node"] == "HeadingNode"


def test_syntax_spec_documents_h4_subpoint_level():
    v1_heading = next(
        block for block in get_syntax_spec(1)["blocks"] if block["name"] == "heading"
    )
    v2_heading = next(
        block for block in get_syntax_spec(2)["blocks"] if block["name"] == "heading"
    )

    assert "[H4]" in v1_heading["description"]
    assert "4" in v2_heading["description"]


def test_explain_syntax_outputs_json_from_syntax_spec(capsys):
    exit_code = cli.main(["--format", "json", "explain-syntax", "--syntax-version", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == cli.ExitCodes.SUCCESS
    assert payload["ok"] is True
    assert payload["command"] == "explain-syntax"
    assert payload["syntaxVersion"] == 2
    assert payload["blocks"][0]["name"] == "document"


def test_explain_syntax_outputs_text_from_syntax_spec(capsys):
    exit_code = cli.main(["explain-syntax", "--syntax-version", "1"])

    captured = capsys.readouterr()

    assert exit_code == cli.ExitCodes.SUCCESS
    assert "Syntax version 1" in captured.out
    assert "[H1] Title" in captured.out
    assert "[IMAGE=diagram.png]" in captured.out
