"""SFU TXT-to-DOCX converter."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sfu-converter")
except PackageNotFoundError:
    __version__ = "0+unknown"
