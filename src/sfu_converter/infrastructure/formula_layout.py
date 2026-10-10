from __future__ import annotations

from sfu_converter.domain.ast_nodes import FormulaSymbol


OPERATOR_SIGNS = ("+", "-", "−", "=", "×", "÷")
DEFAULT_MAX_FORMULA_CHARS = 80


def split_formula_lines(
    content: str,
    continuation_lines: tuple[str, ...] = (),
    *,
    max_chars: int = DEFAULT_MAX_FORMULA_CHARS,
) -> tuple[str, ...]:
    explicit_lines = (content, *continuation_lines)
    if len(explicit_lines) > 1:
        return tuple(line for line in explicit_lines if line != "")

    line = content or ""
    if len(line) <= max_chars:
        return (line,)

    split_at = _last_operator_before(line, max_chars)
    if split_at is None:
        return (line,)

    operator = line[split_at]
    first = line[: split_at + 1].rstrip()
    rest = line[split_at + 1 :].lstrip()
    second = f"{operator} {rest}".rstrip()
    if len(second) > max_chars:
        return (first, *split_formula_lines(second, max_chars=max_chars))
    return (first, second)


def explanation_lines(
    symbols: tuple[FormulaSymbol, ...],
    symbol_numbers: dict[str, str],
) -> tuple[str, ...]:
    if not symbols:
        return ()

    lines = ["где"]
    for symbol in symbols:
        name = symbol.name.strip()
        if symbol.repeats:
            number = symbol_numbers.get(name, "")
            suffix = f"({number})" if number else "(?)"
            lines.append(f"{name} — то же, что и в формуле {suffix}")
        else:
            lines.append(f"{name} — {symbol.description.strip()}")
    return tuple(lines)


def _last_operator_before(text: str, max_chars: int) -> int | None:
    limit = min(len(text) - 1, max_chars)
    for index in range(limit, 0, -1):
        if text[index] in OPERATOR_SIGNS:
            return index
    return None
