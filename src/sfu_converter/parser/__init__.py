"""Parsers that convert TXT syntax into the domain AST."""

from .base import BaseParser, ParserResult
from .v1_parser import V1Parser
from .v2_parser import V2Parser

DEFAULT_SYNTAX_VERSION = 2


def get_parser(syntax_version: int = DEFAULT_SYNTAX_VERSION, *, strict: bool = False) -> BaseParser:
    if syntax_version == 1:
        return V1Parser()
    if syntax_version == 2:
        return V2Parser(strict=strict)
    raise ValueError(f"Unsupported syntax version: {syntax_version}")


__all__ = ["BaseParser", "DEFAULT_SYNTAX_VERSION", "ParserResult", "V1Parser", "V2Parser", "get_parser"]
