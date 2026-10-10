from __future__ import annotations

import re
from datetime import date
from difflib import get_close_matches

from sfu_converter.domain.ast_nodes import Document, ProjectDesignationNode, SectionSetupNode
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile

CODE_DICTIONARY: dict[str, str] = {
    "ПЗ": "Пояснительная записка",
    "РР": "Расчетная работа",
    "ПМ": "Программа и методика испытаний",
    "И": "Инструкция",
    "Д": "Документ",
    "ВС": "Ведомость спецификаций",
    "ВП": "Ведомость покупных изделий",
    "ТБ": "Таблица",
    "ТУ": "Технические условия",
    "СБ": "Сборочный чертеж",
    "ВО": "Ведомость оборудования",
    "ТЧ": "Теоретический чертеж",
    "ГЧ": "Габаритный чертеж",
    "МЭ": "Электромонтажный чертеж",
    "МЧ": "Монтажный чертеж",
    "УЧ": "Упаковочный чертеж",
    "МК": "Монтажный комплект",
    "КТП": "Карта технологического процесса",
    "ОК": "Операционная карта",
    "ВОБ": "Ведомость оборудования",
    "ВМ": "Ведомость материалов",
    "С": "Схема",
    "ЛС": "Локальная смета",
    "ТХ": "Технология производства",
    "ГП": "Генеральный план",
    "ГТ": "Генеральный транспорт",
    "АР": "Архитектурные решения",
    "АС": "Архитектурно-строительные решения",
    "АИ": "Интерьеры",
    "КЖ": "Конструкции железобетонные",
    "КМ": "Конструкции металлические",
    "КМД": "Конструкции металлические деталировочные",
    "КД": "Конструкции деревянные",
    "ВК": "Водоснабжение и канализация",
    "ОВ": "Отопление и вентиляция",
    "ТМ": "Тепломеханические решения",
    "ГСВ": "Газоснабжение внутреннее",
    "ГР": "Газорегуляторный пункт",
    "НВ": "Наружные сети водоснабжения",
    "НК": "Наружные сети канализации",
    "ТС": "Тепловые сети",
    "АД": "Автомобильные дороги",
    "ТР": "Технологические решения",
}

SCHEMA_CODES = frozenset({"Э", "Г", "П", "К", "В", "Л", "Р", "Е", "С"})
SCHEMA_TYPES = frozenset({"1", "2", "3", "4", "5", "6", "7", "0"})
LETTER_NUMERIC_RE = re.compile(
    r"^[А-ЯЁA-Z]{2,3}-\d{2}\.\d{2}\.\d{2}(?:-\d{4})?"
    r"(?:\s+[A-Za-zА-Яа-яЁё0-9]+(?:\.[A-Za-zА-Яа-яЁё0-9]+)*)?"
    r"(?:\s+[А-ЯЁA-Z][0-7])?\s+[А-ЯЁA-Z]{1,3}$"
)

_DESIGNATION_RULE_ID = "project_designations.title_block.letter_numeric_designation"
_PROJECT_PROFILES = {"coursework", "graduation_qualification_work"}


def format_designation(node: ProjectDesignationNode) -> str:
    """Return canonical letter-numeric designation text for a node."""

    head = f"{node.prefix}-{node.specialty_code}"
    if node.year:
        head = f"{head}-{node.year}"
    parts = [head]
    if node.group_code:
        parts.append(node.group_code)
    if node.schema_code or node.schema_type:
        parts.append(f"{node.schema_code or ''}{node.schema_type or ''}")
    parts.append(node.document_code)
    return " ".join(part for part in parts if part)


def validate_designation(
    node: ProjectDesignationNode,
    *,
    current_year: int | None = None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    text = format_designation(node)

    if LETTER_NUMERIC_RE.fullmatch(text) is None:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.PROJECT_DESIGNATION_FORMAT,
                message=f"Project designation '{text}' does not match the letter-numeric format",
                severity=Severity.ERROR,
                rule_id="project_designations.code.format",
                source=node.source,
                data={"designation": text},
            )
        )

    diagnostics.extend(_validate_document_code(node.document_code, node.source))
    diagnostics.extend(_validate_year(node.year, node.source, current_year=current_year))
    diagnostics.extend(_validate_schema(node.schema_code, node.schema_type, node.source))
    return diagnostics


def validate_designation_text(text: str) -> list[Diagnostic]:
    stripped = " ".join((text or "").split())
    if not stripped:
        return [
            Diagnostic(
                code=DiagnosticCodes.PROJECT_DESIGNATION_MISSING,
                message="Main inscription graph 2 must contain a project designation",
                severity=Severity.WARNING,
                rule_id=_DESIGNATION_RULE_ID,
            )
        ]

    diagnostics: list[Diagnostic] = []
    if LETTER_NUMERIC_RE.fullmatch(stripped) is None:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.PROJECT_DESIGNATION_FORMAT,
                message=f"Project designation '{stripped}' does not match the letter-numeric format",
                severity=Severity.ERROR,
                rule_id="project_designations.code.format",
                data={"designation": stripped},
            )
        )
    document_code = stripped.split()[-1]
    diagnostics.extend(_validate_document_code(document_code, None))
    return diagnostics


def validate_document_designations(
    document: Document,
    profile: FormattingProfile,
) -> list[Diagnostic]:
    rule_ids = {rule.id for rule in profile.rules}
    if _DESIGNATION_RULE_ID not in rule_ids and profile.name not in _PROJECT_PROFILES:
        return []

    designations = list(iter_designations(document.blocks))
    if not designations:
        return [
            Diagnostic(
                code=DiagnosticCodes.PROJECT_DESIGNATION_MISSING,
                message="Project profile requires a letter-numeric designation",
                severity=Severity.WARNING,
                rule_id=_DESIGNATION_RULE_ID,
            )
        ]

    diagnostics: list[Diagnostic] = []
    for designation in designations:
        diagnostics.extend(validate_designation(designation))
    return diagnostics


def iter_designations(blocks) -> tuple[ProjectDesignationNode, ...]:
    found: list[ProjectDesignationNode] = []
    for block in blocks:
        if isinstance(block, ProjectDesignationNode):
            found.append(block)
        elif isinstance(block, SectionSetupNode):
            found.extend(iter_designations(block.blocks))
        elif hasattr(block, "blocks"):
            found.extend(iter_designations(getattr(block, "blocks")))
    return tuple(found)


def _validate_document_code(code: str, source) -> list[Diagnostic]:
    if code in CODE_DICTIONARY:
        return []
    suggestions = get_close_matches(code, CODE_DICTIONARY.keys(), n=3)
    if not suggestions:
        suggestions = list(CODE_DICTIONARY.keys())[:3]
    return [
        Diagnostic(
            code=DiagnosticCodes.PROJECT_DESIGNATION_CODE,
            message=(
                f"Unknown document code '{code}'. "
                f"Closest matches: {', '.join(suggestions)}"
            ),
            severity=Severity.ERROR,
            rule_id="project_designations.code.dictionary",
            source=source,
            data={"code": code, "suggestions": tuple(suggestions)},
        )
    ]


def _validate_year(
    year: str | None,
    source,
    *,
    current_year: int | None,
) -> list[Diagnostic]:
    if year is None:
        return []
    upper = (current_year if current_year is not None else date.today().year) + 1
    if year.isdigit() and len(year) == 4 and 1900 <= int(year) <= upper:
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.PROJECT_DESIGNATION_YEAR,
            message=f"Project designation year '{year}' must be in range 1900-{upper}",
            severity=Severity.ERROR,
            rule_id="project_designations.code.format",
            source=source,
            data={"year": year, "min": 1900, "max": upper},
        )
    ]


def _validate_schema(
    schema_code: str | None,
    schema_type: str | None,
    source,
) -> list[Diagnostic]:
    if schema_code is None and schema_type is None:
        return []
    diagnostics: list[Diagnostic] = []
    if schema_code not in SCHEMA_CODES:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.PROJECT_DESIGNATION_SCHEMA,
                message=f"Unknown schema code '{schema_code or ''}'",
                severity=Severity.ERROR,
                rule_id="project_designations.code.dictionary",
                source=source,
                data={"schema_code": schema_code, "allowed": tuple(sorted(SCHEMA_CODES))},
            )
        )
    if schema_type not in SCHEMA_TYPES:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.PROJECT_DESIGNATION_SCHEMA,
                message=f"Unknown schema type '{schema_type or ''}'",
                severity=Severity.ERROR,
                rule_id="project_designations.code.dictionary",
                source=source,
                data={"schema_type": schema_type, "allowed": tuple(sorted(SCHEMA_TYPES))},
            )
        )
    return diagnostics
