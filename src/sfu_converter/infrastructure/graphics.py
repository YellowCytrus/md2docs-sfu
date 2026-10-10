from __future__ import annotations

from collections.abc import Iterable

from sfu_converter.domain.ast_nodes import (
    Document,
    DrawingSheetNode,
    FrameType,
    PosterNode,
    SheetFormat,
    SlideDeckNode,
    TitleBlockForm,
)
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile


def validate(document: Document, profile: FormattingProfile) -> list[Diagnostic]:
    rule_ids = {rule.id for rule in profile.rules}
    diagnostics: list[Diagnostic] = []

    for block in _iter_graphic_blocks(document.blocks):
        if isinstance(block, DrawingSheetNode):
            diagnostics.extend(_validate_drawing(block, profile, rule_ids))
        elif isinstance(block, PosterNode):
            diagnostics.extend(_validate_poster(block, profile, rule_ids))
        elif isinstance(block, SlideDeckNode):
            diagnostics.extend(_validate_slide_deck(block, profile, rule_ids))

    return diagnostics


def _iter_graphic_blocks(blocks: Iterable[object]) -> Iterable[object]:
    for block in blocks:
        if isinstance(block, (DrawingSheetNode, PosterNode, SlideDeckNode)):
            yield block
        child_blocks = getattr(block, "blocks", None)
        if child_blocks is not None:
            yield from _iter_graphic_blocks(child_blocks)


def _validate_drawing(
    node: DrawingSheetNode,
    profile: FormattingProfile,
    rule_ids: set[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if "graphic_and_demonstration_materials.sheet.frame" in rule_ids:
        allowed_forms = _rule_parameters(
            profile,
            "graphic_and_demonstration_materials.sheet.frame",
        ).get("title_block_forms", ("form_5", "form_6"))
        if (
            node.frame is not FrameType.GRAPHIC
            or node.title_block_form is None
            or node.title_block_form.value not in allowed_forms
        ):
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.GRAPHIC_SHEET_FRAME,
                    message="Drawing sheet must use graphic frame with form 5 or 6 title block",
                    severity=Severity.ERROR,
                    rule_id="graphic_and_demonstration_materials.sheet.frame",
                    source=node.source,
                )
            )

    if "graphic_and_demonstration_materials.drawing.scale_set" in rule_ids and node.scale:
        scales = _rule_parameters(
            profile,
            "graphic_and_demonstration_materials.drawing.scale_set",
        ).get("scales", ())
        if node.scale not in scales:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.GRAPHIC_DRAWING_SCALE,
                    message=f"Drawing scale '{node.scale}' is not in the ГОСТ 2.302 scale set",
                    severity=Severity.ERROR,
                    rule_id="graphic_and_demonstration_materials.drawing.scale_set",
                    source=node.source,
                    data={"scale": node.scale},
                )
            )

    if "graphic_and_demonstration_materials.drawing.font_set" in rule_ids and node.font_type:
        font_types = _rule_parameters(
            profile,
            "graphic_and_demonstration_materials.drawing.font_set",
        ).get("font_types", ())
        if node.font_type not in font_types:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.GRAPHIC_DRAWING_FONT,
                    message=f"Drawing font type '{node.font_type}' is not allowed by ГОСТ 2.304",
                    severity=Severity.ERROR,
                    rule_id="graphic_and_demonstration_materials.drawing.font_set",
                    source=node.source,
                    data={"font_type": node.font_type},
                )
            )
    return diagnostics


def _validate_poster(
    node: PosterNode,
    profile: FormattingProfile,
    rule_ids: set[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if "graphic_and_demonstration_materials.poster.fill_density" in rule_ids:
        params = _rule_parameters(profile, "graphic_and_demonstration_materials.poster.fill_density")
        minimum = float(params.get("min_fill_percent", 70))
        fill_percent = node.fill_percent if node.fill_percent is not None else _estimate_poster_fill(node)
        if fill_percent < minimum:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCodes.POSTER_FILL_DENSITY,
                    message=f"Poster fill density {fill_percent:g}% is below required {minimum:g}%",
                    severity=Severity.ERROR,
                    rule_id="graphic_and_demonstration_materials.poster.fill_density",
                    source=node.source,
                    data={"fill_percent": fill_percent, "minimum": minimum},
                )
            )

    if (
        "graphic_and_demonstration_materials.poster.title_block_on_reverse" in rule_ids
        and not node.reverse_title_block
    ):
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.POSTER_TITLE_BLOCK_REVERSE,
                message="Poster title block must be placed on the reverse side",
                severity=Severity.ERROR,
                rule_id="graphic_and_demonstration_materials.poster.title_block_on_reverse",
                source=node.source,
            )
        )
    return diagnostics


def _validate_slide_deck(
    node: SlideDeckNode,
    profile: FormattingProfile,
    rule_ids: set[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if (
        "graphic_and_demonstration_materials.slide.a4_print_out" in rule_ids
        and node.sheet_format is not SheetFormat.A4
    ):
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.SLIDE_A4_PRINT_OUT,
                message="Slide deck must be configured for A4 print-out",
                severity=Severity.ERROR,
                rule_id="graphic_and_demonstration_materials.slide.a4_print_out",
                source=node.source,
            )
        )

    if "graphic_and_demonstration_materials.slide.required_first_slide_fields" in rule_ids:
        diagnostics.extend(_validate_first_slide_fields(node, profile))
    if "graphic_and_demonstration_materials.slide.fill_density" in rule_ids:
        diagnostics.extend(_validate_slide_fill(node, profile))
    if "graphic_and_demonstration_materials.slide.header_continuity" in rule_ids:
        diagnostics.extend(_validate_header_continuity(node))
    return diagnostics


def _validate_first_slide_fields(node: SlideDeckNode, profile: FormattingProfile) -> list[Diagnostic]:
    if not node.slides:
        return []
    first_slide = next((slide for slide in node.slides if slide.first_slide), node.slides[0])
    fields = _rule_parameters(
        profile,
        "graphic_and_demonstration_materials.slide.required_first_slide_fields",
    ).get("fields", ())
    missing = [field for field in fields if not str(first_slide.fields.get(field, "")).strip()]
    if not missing:
        return []
    return [
        Diagnostic(
            code=DiagnosticCodes.SLIDE_REQUIRED_FIRST_FIELDS,
            message=f"First slide is missing required fields: {', '.join(missing)}",
            severity=Severity.ERROR,
            rule_id="graphic_and_demonstration_materials.slide.required_first_slide_fields",
            source=first_slide.source,
            data={"missing": tuple(missing)},
        )
    ]


def _validate_slide_fill(node: SlideDeckNode, profile: FormattingProfile) -> list[Diagnostic]:
    minimum = float(
        _rule_parameters(profile, "graphic_and_demonstration_materials.slide.fill_density").get(
            "min_fill_percent",
            70,
        )
    )
    diagnostics: list[Diagnostic] = []
    for slide in node.slides:
        if slide.fill_percent is None or slide.fill_percent >= minimum:
            continue
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCodes.SLIDE_FILL_DENSITY,
                message=f"Slide fill density {slide.fill_percent:g}% is below required {minimum:g}%",
                severity=Severity.ERROR,
                rule_id="graphic_and_demonstration_materials.slide.fill_density",
                source=slide.source,
                data={"fill_percent": slide.fill_percent, "minimum": minimum},
            )
        )
    return diagnostics


def _validate_header_continuity(node: SlideDeckNode) -> list[Diagnostic]:
    if len(node.slides) < 2:
        return []
    first_title = str(node.slides[0].fields.get("title", "")).strip()
    if not first_title:
        return []
    for slide in node.slides[1:]:
        title = str(slide.fields.get("title", "")).strip()
        if not title or title == first_title:
            continue
        return [
            Diagnostic(
                code=DiagnosticCodes.SLIDE_HEADER_CONTINUITY,
                message="Slide deck title/header must remain continuous across slides",
                severity=Severity.ERROR,
                rule_id="graphic_and_demonstration_materials.slide.header_continuity",
                source=slide.source,
                data={"expected": first_title, "actual": title},
            )
        ]
    return []


def _estimate_poster_fill(node: PosterNode) -> float:
    text_len = len(node.title.strip())
    for block in node.blocks:
        text_len += len(str(getattr(block, "text", "")).strip())
        text_len += len(str(getattr(block, "caption", "") or "").strip())
    return min(100.0, text_len / 10.0)


def _rule_parameters(profile: FormattingProfile, rule_id: str) -> dict:
    for rule in profile.rules:
        if rule.id == rule_id:
            return dict(rule.parameters)
    return {}
