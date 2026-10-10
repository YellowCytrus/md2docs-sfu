from __future__ import annotations

from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Protocol

from sfu_converter.config import PathConfig


class _ReadableResource(Protocol):
    def is_file(self) -> bool: ...

    def read_bytes(self) -> bytes: ...


def packaged_template_exists(template: str | Path) -> bool:
    resource = _packaged_template_resource(template)
    return resource is not None


def packaged_template_bytes(template: str | Path) -> bytes | None:
    resource = _packaged_template_resource(template)
    if resource is None:
        return None
    return resource.read_bytes()


def packaged_template_label(template: str | Path) -> str:
    parts = _template_resource_parts(template)
    return f"package:sfu_converter/{PathConfig.TEMPLATES_DIR}/{'/'.join(parts)}"


def _packaged_template_resource(template: str | Path) -> _ReadableResource | None:
    parts = _template_resource_parts(template)
    if not parts:
        return None
    resource = resources.files("sfu_converter").joinpath(PathConfig.TEMPLATES_DIR, *parts)
    return resource if resource.is_file() else None


def _template_resource_parts(template: str | Path) -> tuple[str, ...]:
    path = Path(template)
    if path.is_absolute():
        return ()

    normalized = PurePosixPath(str(template).replace("\\", "/"))
    parts = tuple(part for part in normalized.parts if part not in ("", "."))
    if not parts or any(part == ".." for part in parts):
        return ()
    if parts[0] == PathConfig.TEMPLATES_DIR:
        parts = parts[1:]
    return parts
