from pathlib import Path

from sfu_converter.config import MeasurementConfig, PathConfig, SyntaxConfig
from sfu_converter.domain.constants import (
    APPENDIX_LETTERS,
    DEFAULT_CITY,
    DEFAULT_PROFILE_NAME,
    EM_DASH,
    EXCLUDED_APPENDIX_LETTERS,
)
from sfu_converter.infrastructure.appendix import APPENDIX_LETTERS as HELPER_APPENDIX_LETTERS
from sfu_converter.menu import ConsoleMenu
from sfu_converter.parser.v1_parser import V1Parser


def test_path_config_exposes_legacy_directory_names_and_log_file():
    assert PathConfig.EXAMPLES_DIR == "examples"
    assert PathConfig.TEMPLATES_DIR == "templates"
    assert PathConfig.RESULTS_DIR == "results"
    assert PathConfig.IMAGES_DIR == "images"
    assert PathConfig.LOGS_DIR == "logs"
    assert PathConfig.LOG_FILENAME == "converter.log"


def test_menu_output_name_uses_path_suffix_for_complex_txt_names(tmp_path):
    menu = ConsoleMenu(tmp_path)

    assert menu.output_name_for("file.txt.backup.txt") == "file.txt.backup.docx"


def test_v1_parser_uses_configured_figure_caption_prefixes():
    result = V1Parser().parse("[IMAGE=diagram.png]\nРис. 1 - Схема")

    assert result.diagnostics == []
    assert result.document.blocks[0].caption == "Рис. 1 - Схема"
    assert "Рис." in SyntaxConfig.FIGURE_CAPTION_PREFIXES


def test_magic_measurement_numbers_are_centralized_in_config():
    assert MeasurementConfig.EMU_PER_CM == 360000

    root = Path(__file__).resolve().parents[1] / "src" / "sfu_converter"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "config.py":
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in ("28.3465", "360000"):
            if forbidden in text:
                offenders.append(f"{path.relative_to(root)} contains {forbidden}")

    assert offenders == []


def test_shared_document_constants_are_centralized():
    assert DEFAULT_PROFILE_NAME == "common"
    assert DEFAULT_CITY == "Красноярск"
    assert EM_DASH == "—"
    assert EXCLUDED_APPENDIX_LETTERS == ("Ё", "З", "Й", "О", "Ч", "Ь", "Ы", "Ъ")
    assert APPENDIX_LETTERS == HELPER_APPENDIX_LETTERS
    assert all(letter not in APPENDIX_LETTERS for letter in EXCLUDED_APPENDIX_LETTERS)


def test_default_profile_literal_is_not_repeated_in_runtime_modules():
    root = Path(__file__).resolve().parents[1] / "src" / "sfu_converter"
    allowed = {
        Path("domain/constants.py"),
        Path("registry/profiles.py"),
    }
    offenders = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if rel in allowed:
            continue
        if '"common"' in path.read_text(encoding="utf-8"):
            offenders.append(str(rel))

    assert offenders == []


def test_menu_avoids_shell_clear_and_fragile_txt_replacement():
    source = Path("src/sfu_converter/menu.py").read_text(encoding="utf-8")

    assert "os.system" not in source
    assert ".replace('.txt', '.docx')" not in source

