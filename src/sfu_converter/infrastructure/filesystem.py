from __future__ import annotations

from pathlib import Path

from sfu_converter.ports.file_io import FileReaderPort, FileWriterPort


class LocalFilesystem(FileReaderPort, FileWriterPort):
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        return Path(path).read_text(encoding=encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
