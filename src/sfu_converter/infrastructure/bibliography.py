from __future__ import annotations

import re
from enum import Enum
from typing import Iterable

from sfu_converter.domain.ast_nodes import BibliographyEntryNode, SourceRecordNode, SourceRecordType, SourceSpan
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity


class BibliographyGroupingMethod(str, Enum):
    ALPHABETICAL = "alphabetical"
    SYSTEMATIC = "systematic"
    CHRONOLOGICAL = "chronological"


_REQUIRED_FIELDS: dict[SourceRecordType, tuple[str, ...]] = {
    SourceRecordType.NORMATIVE: ("title", "city", "publisher", "year"),
    SourceRecordType.PATENT: (
        "country",
        "number",
        "title",
        "mki",
        "applicant",
        "applied_date",
        "published_date",
    ),
    SourceRecordType.BOOK_ONE_AUTHOR: ("authors", "title", "city", "publisher", "year", "pages"),
    SourceRecordType.BOOK_TWO_AUTHORS: ("authors", "title", "city", "publisher", "year", "pages"),
    SourceRecordType.BOOK_THREE_AUTHORS: ("authors", "title", "city", "publisher", "year", "pages"),
    SourceRecordType.BOOK_FOUR_PLUS_AUTHORS: ("authors", "title", "city", "publisher", "year", "pages"),
    SourceRecordType.VOLUME: ("authors", "title", "volume", "city", "publisher", "year", "pages"),
    SourceRecordType.DISSERTATION: ("author", "title", "degree", "city", "year", "pages"),
    SourceRecordType.ELECTRONIC: ("title", "url", "accessed"),
    SourceRecordType.ARTICLE: ("authors", "title", "journal", "year", "number", "pages"),
}

_ELECTRONIC_ENTRY_RE = re.compile(r"\b(?:URL\s*:|https?://|www\.|Электронный ресурс)", re.IGNORECASE)
_ACCESS_DATE_RE = re.compile(r"\(дата\s+обращения\s*:\s*\d{2}\.\d{2}\.\d{4}\)", re.IGNORECASE)


def format_record(record: SourceRecordNode) -> str:
    formatter = _FORMATTERS[record.record_type]
    return formatter(record)


def validate_records(
    records: Iterable[SourceRecordNode],
    *,
    grouping_method: BibliographyGroupingMethod = BibliographyGroupingMethod.ALPHABETICAL,
) -> list[Diagnostic]:
    records = tuple(records)
    diagnostics: list[Diagnostic] = []
    for record in records:
        diagnostics.extend(_validate_required_fields(record))
        diagnostics.extend(_validate_gost_separators(record))

    diagnostics.extend(_validate_grouping(records, grouping_method))
    diagnostics.extend(_validate_russian_first(records))
    return diagnostics


def validate_entries(entries: Iterable[BibliographyEntryNode]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for entry in entries:
        if not _requires_access_date(entry.text):
            continue
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.BIBLIOGRAPHY_ACCESS_DATE,
                message=(
                    f"Bibliography entry {entry.number} with URL or electronic resource "
                    "must include '(дата обращения: ДД.ММ.ГГГГ)' after the URL or source title"
                ),
                severity=Severity.WARNING,
                source=entry.source,
                rule_id="common.bibliography.gost_record",
                data={"record_number": entry.number},
            )
        )
    return diagnostics


def _requires_access_date(text: str) -> bool:
    return _ELECTRONIC_ENTRY_RE.search(text) is not None and _ACCESS_DATE_RE.search(text) is None


def _validate_required_fields(record: SourceRecordNode) -> list[Diagnostic]:
    missing = [
        field
        for field in _REQUIRED_FIELDS[record.record_type]
        if not str(record.fields.get(field, "")).strip()
    ]
    if not missing:
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.BIBLIOGRAPHY_MISSING_FIELD,
            message=(
                f"Source record {record.number} ({record.record_type.value}) "
                f"missing required field(s): {', '.join(missing)}"
            ),
            severity=Severity.ERROR,
            source=record.source,
            rule_id="common.bibliography.gost_record",
            data={"record_number": record.number, "missing": tuple(missing)},
        )
    ]


def _validate_gost_separators(record: SourceRecordNode) -> list[Diagnostic]:
    if _validate_required_fields(record):
        return []
    formatted = format_record(record)
    if " — " in formatted and ". — " in formatted:
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.BIBLIOGRAPHY_SEPARATOR,
            message=f"Source record {record.number} must use GOST separators such as ' — '",
            severity=Severity.WARNING,
            source=record.source,
            rule_id="common.bibliography.gost_record",
            data={"record_number": record.number},
        )
    ]


def _validate_grouping(
    records: tuple[SourceRecordNode, ...],
    grouping_method: BibliographyGroupingMethod,
) -> list[Diagnostic]:
    if len(records) < 2:
        return []
    detected: list[BibliographyGroupingMethod] = []
    if _is_alphabetical(records):
        detected.append(BibliographyGroupingMethod.ALPHABETICAL)
    if _is_chronological(records):
        detected.append(BibliographyGroupingMethod.CHRONOLOGICAL)
    if _is_systematic(records):
        detected.append(BibliographyGroupingMethod.SYSTEMATIC)

    if len(detected) <= 1 and (not detected or detected[0] is grouping_method):
        return []
    methods = tuple(method.value for method in detected or (grouping_method,))
    return [
        Diagnostic(
            code=DiagnosticCodes.BIBLIOGRAPHY_GROUPING_METHOD,
            message=(
                "Bibliography grouping mixes or conflicts with selected method: "
                + ", ".join(methods)
            ),
            severity=Severity.WARNING,
            rule_id="common.bibliography.grouping_method",
            data={"methods": methods, "selected": grouping_method.value},
        )
    ]


def _validate_russian_first(records: tuple[SourceRecordNode, ...]) -> list[Diagnostic]:
    seen_foreign = False
    for record in records:
        if record.language.casefold() != "ru":
            seen_foreign = True
            continue
        if seen_foreign:
            return [
                Diagnostic(
                    code=DiagnosticCodes.BIBLIOGRAPHY_RUSSIAN_FIRST,
                    message="Russian-language bibliography entries must precede foreign-language entries",
                    severity=Severity.WARNING,
                    source=record.source,
                    rule_id="common.bibliography.russian_first",
                    data={"record_number": record.number},
                )
            ]
    return []


def _format_normative(record: SourceRecordNode) -> str:
    f = record.fields
    return f"{f['title']}. — {f['city']}: {f['publisher']}, {f['year']}."


def _format_patent(record: SourceRecordNode) -> str:
    f = record.fields
    return (
        f"Пат. {f['number']} {f['country']}, МКИ {f['mki']}. {f['title']} / "
        f"{f['applicant']}; заявл. {f['applied_date']}; опубл. {f['published_date']}."
    )


def _format_book(record: SourceRecordNode) -> str:
    f = record.fields
    authors = _authors(f["authors"])
    lead = _bibliographic_author(authors[0])
    slash = ", ".join(_initials_first(author) for author in authors)
    return f"{lead} {f['title']} / {slash}. — {f['city']}: {f['publisher']}, {f['year']}. — {f['pages']} с."


def _format_volume(record: SourceRecordNode) -> str:
    f = record.fields
    return _format_book(record).replace(f". — {f['pages']} с.", f". — Т. {f['volume']}. — {f['pages']} с.")


def _format_dissertation(record: SourceRecordNode) -> str:
    f = record.fields
    author = _bibliographic_author(f["author"])
    return f"{author} {f['title']}: дис. ... {f['degree']}. — {f['city']}, {f['year']}. — {f['pages']} с."


def _format_electronic(record: SourceRecordNode) -> str:
    f = record.fields
    return f"{f['title']} [Электронный ресурс]. — URL: {f['url']} (дата обращения: {f['accessed']})."


def _format_article(record: SourceRecordNode) -> str:
    f = record.fields
    authors = _authors(f["authors"])
    lead = _bibliographic_author(authors[0])
    slash = ", ".join(_initials_first(author) for author in authors)
    return f"{lead} {f['title']} / {slash} // {f['journal']}. — {f['year']}. — № {f['number']}. — С. {f['pages']}."


_FORMATTERS = {
    SourceRecordType.NORMATIVE: _format_normative,
    SourceRecordType.PATENT: _format_patent,
    SourceRecordType.BOOK_ONE_AUTHOR: _format_book,
    SourceRecordType.BOOK_TWO_AUTHORS: _format_book,
    SourceRecordType.BOOK_THREE_AUTHORS: _format_book,
    SourceRecordType.BOOK_FOUR_PLUS_AUTHORS: _format_book,
    SourceRecordType.VOLUME: _format_volume,
    SourceRecordType.DISSERTATION: _format_dissertation,
    SourceRecordType.ELECTRONIC: _format_electronic,
    SourceRecordType.ARTICLE: _format_article,
}


def _authors(value: str) -> tuple[str, ...]:
    return tuple(author.strip() for author in value.split(",") if author.strip())


def _bibliographic_author(author: str) -> str:
    parts = author.split()
    if len(parts) < 2:
        return author
    return f"{parts[0]}, {' '.join(parts[1:])}"


def _initials_first(author: str) -> str:
    parts = author.split()
    if len(parts) < 2:
        return author
    return f"{' '.join(parts[1:])} {parts[0]}"


def _sort_key(record: SourceRecordNode) -> str:
    if "authors" in record.fields:
        return _authors(record.fields["authors"])[0].casefold()
    return record.fields.get("author", record.fields.get("title", "")).casefold()


def _year(record: SourceRecordNode) -> int | None:
    raw = record.fields.get("year")
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def _is_alphabetical(records: tuple[SourceRecordNode, ...]) -> bool:
    keys = [_sort_key(record) for record in records]
    return keys == sorted(keys)


def _is_chronological(records: tuple[SourceRecordNode, ...]) -> bool:
    years = [_year(record) for record in records]
    if any(year is None for year in years):
        return False
    concrete_years = [year for year in years if year is not None]
    return concrete_years == sorted(concrete_years) or concrete_years == sorted(concrete_years, reverse=True)


def _is_systematic(records: tuple[SourceRecordNode, ...]) -> bool:
    types = [record.record_type for record in records]
    return len(set(types)) > 1 and types == sorted(types, key=lambda item: item.value)


def source_span_for_records(records: tuple[SourceRecordNode, ...]) -> SourceSpan | None:
    for record in records:
        if record.source is not None:
            return record.source
    return None
