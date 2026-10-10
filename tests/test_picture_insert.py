import logging

import pytest
from docx import Document
from docx.shared import Cm
from PIL import Image

from sfu_converter.config import SIBFUConfig
from sfu_converter.utils_image_insert import (
    calculate_image_dimensions,
    convert_image_to_rgb,
    insert_image,
    save_image_to_buffer,
)


@pytest.fixture
def sample_image(tmp_path):
    img = Image.new("RGB", (200, 100), color="red")
    path = tmp_path / "test.png"
    img.save(str(path))
    return path


@pytest.fixture
def rgba_image(tmp_path):
    img = Image.new("RGBA", (200, 100), color=(255, 0, 0, 128))
    path = tmp_path / "test_rgba.png"
    img.save(str(path))
    return path


class TestConvertImageToRgb:
    def test_rgb_passthrough(self, sample_image):
        img = Image.open(str(sample_image))

        result = convert_image_to_rgb(img)

        assert result.mode == "RGB"

    def test_rgba_conversion(self, rgba_image):
        img = Image.open(str(rgba_image))

        result = convert_image_to_rgb(img)

        assert result.mode == "RGB"


class TestCalculateImageDimensions:
    def test_dimensions_within_max_width(self):
        width, height = calculate_image_dimensions(
            original_size=(1000, 500),
            width=None,
            height=None,
            max_width=Cm(15),
            dpi=96,
        )

        assert width is not None
        assert height is not None
        assert width <= Cm(15)


class TestSaveImageToBuffer:
    def test_saves_rgb_image_to_buffer(self, sample_image):
        img = Image.open(str(sample_image))

        buffer = save_image_to_buffer(img, format="PNG")

        assert buffer.getbuffer().nbytes > 0


class TestInsertImage:
    def test_insert_into_document(self, sample_image, tmp_path):
        doc = Document()
        logger = logging.getLogger("test")

        inserted = insert_image(doc, str(sample_image), SIBFUConfig.IMAGE, logger)

        output = tmp_path / "output.docx"
        doc.save(str(output))
        assert inserted is True
        assert output.exists()
        assert len(doc.inline_shapes) == 1
