import importlib
from importlib import resources
from importlib.metadata import version as dist_version
from pathlib import Path
from unittest.mock import patch

import tomllib

from sfu_converter.cli import _template_exists


def test_package_exposes_version():
    package = importlib.import_module("sfu_converter")

    assert package.__version__ == dist_version("sfu-converter")


def test_package_version_falls_back_when_distribution_metadata_is_missing():
    metadata = importlib.import_module("importlib.metadata")
    package = importlib.import_module("sfu_converter")

    def missing_version(distribution_name):
        assert distribution_name == "sfu-converter"
        raise metadata.PackageNotFoundError(distribution_name)

    with patch.object(metadata, "version", missing_version):
        reloaded = importlib.reload(package)
        assert reloaded.__version__ == "0+unknown"

    importlib.reload(package)


def test_module_entrypoint_imports_main_function():
    entrypoint = importlib.import_module("sfu_converter.__main__")
    cli_module = importlib.import_module("sfu_converter.cli")

    assert entrypoint.main is cli_module.main


def test_runtime_package_data_is_declared():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.setuptools.package-data]" in pyproject
    assert '"cli_schemas/*.json"' in pyproject
    assert '"templates/*.docx"' in pyproject


def test_release_build_uses_git_tag_versioning():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert any(requirement.startswith("setuptools-scm") for requirement in pyproject["build-system"]["requires"])
    assert "setuptools_scm" in pyproject["tool"]
    assert "version" not in pyproject["tool"].get("setuptools", {}).get("dynamic", {})


def test_license_metadata_uses_spdx_expression():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'license = "MIT"' in pyproject
    assert "License :: OSI Approved :: MIT License" not in pyproject


def test_default_template_is_packaged_resource():
    template = resources.files("sfu_converter").joinpath("templates", "template1.docx")

    assert template.is_file()


def test_cli_accepts_packaged_default_template(tmp_path):
    assert _template_exists(tmp_path, Path("template1.docx"))
