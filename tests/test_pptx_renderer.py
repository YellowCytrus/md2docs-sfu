from zipfile import ZipFile

from sfu_converter import cli
from sfu_converter.infrastructure.pptx_renderer import PptxRenderer
from sfu_converter.parser import V2Parser
from sfu_converter.registry import get_profile


def _slide_count(path) -> int:
    with ZipFile(path) as package:
        return len(
            [
                name
                for name in package.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ]
        )


def test_pptx_renderer_writes_expected_slide_count(tmp_path):
    document = V2Parser().parse(
        "\n".join(
            [
                "[SLIDE_DECK format=A4]",
                (
                    '[SLIDE first_slide=true title="Тема" student="Иванов" supervisor="Петров" '
                    'university="СФУ" institute="ИКИТ" city="Красноярск" year=2026][/SLIDE]'
                ),
                '[SLIDE title="Тема"][/SLIDE]',
                "[/SLIDE_DECK]",
            ]
        )
    ).document
    output = tmp_path / "deck.pptx"

    diagnostics = PptxRenderer().render_to_file(document, get_profile("graphic_and_demonstration_materials"), str(output))

    assert diagnostics == []
    assert _slide_count(output) == 2


def test_convert_command_supports_pptx_output_format(tmp_path):
    source = tmp_path / "deck.txt"
    source.write_text(
        "\n".join(
            [
                "[SLIDE_DECK format=A4]",
                (
                    '[SLIDE first_slide=true title="Тема" student="Иванов" supervisor="Петров" '
                    'university="СФУ" institute="ИКИТ" city="Красноярск" year=2026][/SLIDE]'
                ),
                '[SLIDE title="Тема"][/SLIDE]',
                "[/SLIDE_DECK]",
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "deck.pptx"

    exit_code = cli.main(
        [
            "--quiet",
            "convert",
            "--input",
            str(source),
            "--output",
            str(output),
            "--syntax-version",
            "2",
            "--profile",
            "graphic_and_demonstration_materials",
            "--output-format",
            "pptx",
        ]
    )

    assert exit_code == 0
    assert _slide_count(output) == 2
