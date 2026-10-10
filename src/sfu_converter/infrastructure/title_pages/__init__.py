"""Title page form registry and dispatcher."""
from __future__ import annotations

from typing import Any

from sfu_converter.infrastructure.title_pages.base import TitlePageForm, TitlePageLayout
from sfu_converter.infrastructure.title_pages import (
    form_b,
    form_d,
    form_e,
    form_g,
    form_i,
    form_k,
    form_l,
    form_m,
    form_n,
    form_v,
    form_zh,
    generic,
)

_FORM_MODULES = (
    form_b, form_v, form_g, form_d, form_e, form_zh,
    form_i, form_k, form_l, form_m, form_n,
)

FORM_REGISTRY: dict[str, TitlePageForm] = {}

for _mod in _FORM_MODULES:
    FORM_REGISTRY[_mod.FORM_ID] = TitlePageForm(
        form_id=_mod.FORM_ID,
        default_document_type=_mod.DEFAULT_DOCUMENT_TYPE,
        required_metadata=_mod.REQUIRED_METADATA,
        optional_metadata=_mod.OPTIONAL_METADATA,
        render=_mod.render,
    )

GENERIC_FORM = TitlePageForm(
    form_id=generic.FORM_ID,
    default_document_type=generic.DEFAULT_DOCUMENT_TYPE,
    required_metadata=generic.REQUIRED_METADATA,
    optional_metadata=generic.OPTIONAL_METADATA,
    render=generic.render,
)

_RULE_ID_TO_FORM: dict[str, str] = {
    "graduation_qualification_work.title_page.form_b": "form_b",
    "graduation_qualification_work.title_page.form_v": "form_v",
    "graduation_qualification_work.title_page.form_g": "form_g",
    "graduation_qualification_work.title_page.form_d": "form_d",
    "graduation_qualification_work.title_page.form_e": "form_e",
    "graduation_qualification_work.title_page.form_zh": "form_zh",
    "coursework.title_page.form_i": "form_i",
    "practice_reports.title_page.form_k": "form_k",
    "research_reports.title_page.form_l": "form_l",
    "lab_practical_project_reports.title_page.form_m": "form_m",
    "small_written_works.title_page.form_n": "form_n",
}


def select_title_page_form(
    profile,
    metadata: dict[str, Any],
    *,
    override: str | None = None,
) -> TitlePageForm:
    if override:
        if override in FORM_REGISTRY:
            return FORM_REGISTRY[override]
        try:
            from sfu_converter.registry import get_profile
            override_profile = get_profile(override)
            form = _form_for_profile(override_profile)
            if form is not None:
                return form
        except KeyError:
            pass

    if profile is not None:
        form = _form_for_profile(profile)
        if form is not None:
            return form

    return GENERIC_FORM


def _form_for_profile(profile) -> TitlePageForm | None:
    from sfu_converter.domain.formatting import RuleStatus
    for rule in profile.rules:
        if ".title_page.form" in rule.id and rule.renderer_status is RuleStatus.IMPLEMENTED:
            form_id = _RULE_ID_TO_FORM.get(rule.id)
            if form_id and form_id in FORM_REGISTRY:
                return FORM_REGISTRY[form_id]
    return None


__all__ = [
    "FORM_REGISTRY",
    "GENERIC_FORM",
    "TitlePageForm",
    "TitlePageLayout",
    "select_title_page_form",
]
