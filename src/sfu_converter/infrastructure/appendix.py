from __future__ import annotations

from dataclasses import replace

from sfu_converter.domain.constants import APPENDIX_LETTERS, APPENDIX_TITLE
from sfu_converter.domain.ast_nodes import AppendixNode, Document
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity


_APPENDIX_INDEX = {letter: index for index, letter in enumerate(APPENDIX_LETTERS)}


def assign_appendix_letters(document: Document) -> tuple[Document, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    state = _LetterState()
    blocks = tuple(_assign_block(block, state, diagnostics) for block in document.blocks)
    if blocks == document.blocks:
        return document, diagnostics
    return replace(document, blocks=blocks), diagnostics


def _assign_block(block, state: "_LetterState", diagnostics: list[Diagnostic]):
    if isinstance(block, AppendixNode):
        return _assign_appendix(block, state, diagnostics)
    return block


def _assign_appendix(
    block: AppendixNode,
    state: "_LetterState",
    diagnostics: list[Diagnostic],
) -> AppendixNode:
    letter = block.letter
    emitted = False
    if letter is None:
        letter = state.next_letter()
        emitted = True
    else:
        letter = letter.upper()
        state.observe(letter)

    updated = replace(
        block,
        letter=letter,
        id=block.id or f"app:{letter.lower()}",
        title=_title_with_letter(block.title, letter),
    )

    if emitted:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.APPENDIX_AUTOLETTER_ASSIGNED,
                message=f"Appendix at position {state.position} assigned letter {letter}",
                severity=Severity.INFO,
                source=block.source,
                rule_id="common.appendix.auto_letter",
                data={"letter": letter, "position": state.position},
            )
        )
    return updated


def _title_with_letter(title: str, letter: str) -> str:
    text = (title or APPENDIX_TITLE).strip()
    upper = text.upper()
    if APPENDIX_TITLE in upper and letter in upper:
        return text
    if upper == APPENDIX_TITLE:
        return f"{APPENDIX_TITLE} {letter}"
    return text


class _LetterState:
    def __init__(self) -> None:
        self._next_index = 0
        self.position = 0

    def observe(self, letter: str) -> None:
        self.position += 1
        if letter in _APPENDIX_INDEX:
            self._next_index = max(self._next_index, _APPENDIX_INDEX[letter] + 1)

    def next_letter(self) -> str:
        self.position += 1
        if self._next_index >= len(APPENDIX_LETTERS):
            return APPENDIX_LETTERS[-1]
        letter = APPENDIX_LETTERS[self._next_index]
        self._next_index += 1
        return letter
