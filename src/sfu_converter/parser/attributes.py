from __future__ import annotations

import re

_ATTR_RE = re.compile(r'(\w+)=(?:"([^"]*)"|([^\s\]]+))')


def parse_attributes(text: str) -> dict[str, str]:
    """Parse key=value attributes with optional quoted values."""

    return {
        match.group(1): match.group(2) if match.group(2) is not None else match.group(3)
        for match in _ATTR_RE.finditer(text)
    }
