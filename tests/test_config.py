from docx.shared import Cm

from sfu_converter.config import SIBFUConfig
from sfu_converter.utils_image_insert import (
    _from_emu_to_cm,
    calculate_image_dimensions,
)


def assert_length_close(actual, expected):
    assert abs(actual - expected) < 1000


def test_image_max_width_matches_page_text_area():
    assert_length_close(SIBFUConfig.IMAGE["max_width"], Cm(15))


def test_right_margin_matches_sfu_standard():
    assert_length_close(SIBFUConfig.MARGINS["right"], Cm(1))


def test_from_emu_to_cm_uses_docx_cm_scale():
    assert_length_close(_from_emu_to_cm(360000), Cm(1))


def test_calculate_image_dimensions_caps_large_image_to_max_width():
    width, height = calculate_image_dimensions(
        original_size=(3000, 1500),
        max_width=Cm(15),
        dpi=96,
    )

    assert width is not None
    assert height is not None
    assert_length_close(width, Cm(15))
    assert_length_close(height, Cm(7.5))
