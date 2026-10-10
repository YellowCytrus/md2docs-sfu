"""Convert LaTeX snippets to Word OMML equations with pandoc.

Pandoc implements a native TeX -> OMML writer, so we shell out to it and lift
the resulting ``<m:oMath>`` elements out of a throwaway DOCX.  Conversions are
batched: every unique expression for a document is converted in a single pandoc
invocation (pandoc startup dominates the cost) and cached per renderer.

If pandoc is not installed the converter degrades gracefully: ``convert``
returns ``None`` and the renderer falls back to plain text so no content is
lost.
"""

from __future__ import annotations

import copy
import logging
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

from lxml import etree

OMML_NAMESPACE = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_OMML = f"{{{OMML_NAMESPACE}}}"
_WORD = f"{{{_WORD_NAMESPACE}}}"

_TOKEN_PREFIX = "SFUMATHTOKEN"
_TOKEN_SUFFIX = "ENDTOKEN"

# ``$...$`` and ``\(...\)`` are the inline-math delimiters recognised in V2 TXT.
_INLINE_MATH_RE = re.compile(r"\$([^$\n]+)\$|\\\((.+?)\\\)", re.DOTALL)


def split_inline_math(text: str) -> list[tuple[str, str]]:
    """Split *text* into ``("text"|"math", value)`` segments.

    Consecutive plain text is returned untouched; every ``$...$`` or
    ``\\(...\\)`` region becomes a ``"math"`` segment holding the raw LaTeX.
    """

    segments: list[tuple[str, str]] = []
    cursor = 0
    for match in _INLINE_MATH_RE.finditer(text):
        if match.start() > cursor:
            segments.append(("text", text[cursor : match.start()]))
        value = match.group(1) if match.group(1) is not None else match.group(2)
        segments.append(("math", value))
        cursor = match.end()
    if cursor < len(text):
        segments.append(("text", text[cursor:]))
    if not segments:
        return [("text", text)]
    return segments


def has_inline_math(text: str) -> bool:
    """Whether *text* contains a recognisable inline-math region."""

    return _INLINE_MATH_RE.search(text) is not None


class LatexMathConverter:
    """LaTeX -> OMML conversion backed by pandoc, with per-document batching."""

    def __init__(self, logger=None, pandoc_path: str | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self._pandoc_path = pandoc_path or shutil.which("pandoc")
        self._cache: dict[str, etree._Element | None] = {}

    @property
    def available(self) -> bool:
        return self._pandoc_path is not None

    def prefetch(self, expressions: Iterable[str]) -> None:
        """Convert every not-yet-cached expression in one batched pandoc call."""

        wanted = [
            expression
            for expression in dict.fromkeys(expressions)
            if expression and expression.strip() and expression not in self._cache
        ]
        if not wanted:
            return
        if not self.available:
            for expression in wanted:
                self._cache[expression] = None
            self.logger.warning(
                "pandoc not found: LaTeX formulas will be rendered as plain text"
            )
            return
        self._cache.update(self._convert_batch(wanted))

    def convert(self, latex: str) -> etree._Element | None:
        """Return a fresh ``<m:oMath>`` element for *latex*, or ``None``."""

        if latex not in self._cache:
            self.prefetch([latex])
        element = self._cache.get(latex)
        return copy.deepcopy(element) if element is not None else None

    def _convert_batch(self, expressions: list[str]) -> dict[str, etree._Element | None]:
        results: dict[str, etree._Element | None] = {expr: None for expr in expressions}
        tokens = {self._token(index): expr for index, expr in enumerate(expressions)}
        markdown = "\n\n".join(
            f"{token} ${expression.strip()}$ {token}"
            for token, expression in tokens.items()
        )
        document_xml = self._run_pandoc(markdown + "\n")
        if document_xml is None:
            return results
        try:
            root = etree.fromstring(document_xml)
        except etree.XMLSyntaxError as exc:
            self.logger.warning("Could not parse pandoc output: %s", exc)
            return results
        for token, expression in tokens.items():
            results[expression] = _extract_omath_for_token(root, token)
        return results

    @staticmethod
    def _token(index: int) -> str:
        return f"{_TOKEN_PREFIX}{index}{_TOKEN_SUFFIX}"

    def _run_pandoc(self, markdown: str) -> bytes | None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "formulas.md"
            target = Path(tmp_dir) / "formulas.docx"
            source.write_text(markdown, encoding="utf-8")
            try:
                subprocess.run(
                    [self._pandoc_path, "-f", "markdown", "-t", "docx", str(source), "-o", str(target)],
                    check=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                self.logger.warning("pandoc LaTeX conversion failed: %s", exc)
                return None
            try:
                with zipfile.ZipFile(target) as archive:
                    return archive.read("word/document.xml")
            except (KeyError, zipfile.BadZipFile) as exc:
                self.logger.warning("Could not read pandoc DOCX output: %s", exc)
                return None


def _extract_omath_for_token(root: etree._Element, token: str) -> etree._Element | None:
    for paragraph in root.iter(f"{_WORD}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_WORD}t"))
        if token in text:
            return paragraph.find(f".//{_OMML}oMath")
    return None
