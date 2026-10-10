from sfu_converter.tools.check_cyrillic_markers import check_file
from sfu_converter.tools.fix_cyrillic_markers import (
    find_markers,
    fix_file,
    fix_marker_content,
    verify_file,
)


def test_check_file_reports_cyrillic_marker_characters(tmp_path):
    source = tmp_path / "bad_marker.txt"
    source.write_text("[Н1] Заголовок\n[TABLE_START]\n", encoding="utf-8")

    issues = check_file(source)

    assert issues == [
        {
            "line": 1,
            "marker": "Н1",
            "char": "Н",
            "suggestion": "H",
            "text": "[Н1] Заголовок",
        }
    ]


def test_find_markers_returns_marker_positions():
    assert find_markers("before [Н1] after") == [
        {"start": 7, "end": 11, "content": "Н1", "full": "[Н1]"}
    ]


def test_fix_marker_content_replaces_only_marker_homoglyphs():
    fixed, changes = fix_marker_content("ТABLE_START")

    assert fixed == "TABLE_START"
    assert changes == ["Т"]


def test_fix_file_rewrites_markers_and_verify_file_confirms(tmp_path):
    source = tmp_path / "bad_marker.txt"
    source.write_text("[Н1] Заголовок\n[ТABLE_START]\n", encoding="utf-8")

    stats = fix_file(source, create_backup=False)

    assert stats["fixed"] == 2
    assert source.read_text(encoding="utf-8") == "[H1] Заголовок\n[TABLE_START]\n"
    assert verify_file(source) == []
