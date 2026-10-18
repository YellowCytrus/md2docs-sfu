"""Typographic dash normalisation shared by parsers, renderers and captions.

Russian academic typography separates the parts of a sentence with an em dash
(U+2014). Authors type it as a run of ASCII hyphens ("Узел G --- Astra Linux"),
which would otherwise reach the DOCX verbatim as "---".

Normalising in the parser keeps the rendered heading and the generated table of
contents in agreement -- the ``common.toc.matches_headings`` rule compares the
two, so normalising only the ToC would make them disagree.

Only runs that act as separators are touched: two or more hyphens, or a lone
hyphen/en dash between spaces. Ranges and compound words ("1990-1995",
"ДОС-ный") carry a single hyphen without surrounding spaces and are left alone.
"""

from __future__ import annotations

import re

from sfu_converter.domain.constants import DASH_SEPARATOR, EN_DASH

# Two or more ASCII hyphens acting as a separator, with optional padding.
_DASH_RUN_RE = re.compile(r"[ \t]*-{2,}[ \t]*")
# A single ASCII hyphen or en dash surrounded by spaces; the spaces are part of
# the match so that the replacement does not double them up. Requiring a space on
# both sides keeps ranges and compound words ("1990-1995", "ДОС-ный") intact.
_LONE_SEPARATOR_RE = re.compile(rf"[ \t]+[-{EN_DASH}][ \t]+")


def normalize_dashes(text: str) -> str:
    """Return *text* with dash separators replaced by an em dash."""

    if not text:
        return text
    if "-" not in text and EN_DASH not in text:
        return text

    was_trimmed = text == text.strip()
    text = _DASH_RUN_RE.sub(DASH_SEPARATOR, text)
    text = _LONE_SEPARATOR_RE.sub(DASH_SEPARATOR, text)
    return text.strip() if was_trimmed else text