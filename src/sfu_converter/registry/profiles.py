"""Formatting profiles defined for each SFU document family.

Each profile lists the source documents from which its rules are derived plus
the resolved tuple of :class:`FormattingRule` objects. The ``common`` profile
holds the shared baseline; document-specific profiles inherit those rules and
will gain additional ones as further docs are translated to the registry.
"""

from __future__ import annotations

from sfu_converter.domain.formatting import FormattingProfile
from sfu_converter.registry.rules import (
    COMMON_RULES,
    COURSEWORK_RULES,
    GRADUATION_QUALIFICATION_WORK_RULES,
    GRAPHIC_AND_DEMONSTRATION_MATERIAL_RULES,
    LAB_PRACTICAL_PROJECT_REPORT_RULES,
    PRACTICE_REPORT_RULES,
    PROJECT_DESIGNATION_RULES,
    RESEARCH_REPORT_RULES,
    SMALL_WRITTEN_WORK_RULES,
)

_COMMON_DOC = "docs/formatting requirements/common.md"
_COURSEWORK_DOC = "docs/formatting requirements/coursework.md"
_GRADUATION_DOC = "docs/formatting requirements/graduation_qualification_work.md"
_GRAPHIC_DOC = "docs/formatting requirements/graphic_and_demonstration_materials.md"
_LAB_DOC = "docs/formatting requirements/lab_practical_project_reports.md"
_PRACTICE_DOC = "docs/formatting requirements/practice_reports.md"
_PROJECT_DESIGNATION_DOC = "docs/formatting requirements/project_designations.md"
_RESEARCH_DOC = "docs/formatting requirements/research_reports.md"
_SMALL_WRITTEN_DOC = "docs/formatting requirements/small_written_works.md"


def _profile(
    name: str,
    display_name: str,
    extra_docs: tuple[str, ...] = (),
    extra_rules=(),
) -> FormattingProfile:
    return FormattingProfile(
        name=name,
        display_name=display_name,
        source_docs=(_COMMON_DOC, *extra_docs),
        rules=(*COMMON_RULES, *extra_rules),
    )


PROFILES: dict[str, FormattingProfile] = {
    "common": FormattingProfile(
        name="common",
        display_name="Common formatting rules",
        source_docs=(_COMMON_DOC,),
        rules=COMMON_RULES,
    ),
    "lab_practical_project_reports": _profile(
        "lab_practical_project_reports",
        "Lab / Practical / Project Reports",
        (_LAB_DOC,),
        LAB_PRACTICAL_PROJECT_REPORT_RULES,
    ),
    "practice_reports": _profile(
        "practice_reports",
        "Practice Reports",
        (_PRACTICE_DOC,),
        PRACTICE_REPORT_RULES,
    ),
    "research_reports": _profile(
        "research_reports",
        "Research-Work Reports",
        (_RESEARCH_DOC,),
        RESEARCH_REPORT_RULES,
    ),
    "coursework": _profile(
        "coursework",
        "Course Project / Course Work",
        (_COURSEWORK_DOC, _PROJECT_DESIGNATION_DOC, _GRAPHIC_DOC),
        (*COURSEWORK_RULES, *PROJECT_DESIGNATION_RULES, *GRAPHIC_AND_DEMONSTRATION_MATERIAL_RULES),
    ),
    "graduation_qualification_work": _profile(
        "graduation_qualification_work",
        "Graduation Qualification Work (VKR)",
        (_GRADUATION_DOC, _GRAPHIC_DOC, _PROJECT_DESIGNATION_DOC),
        (
            *GRADUATION_QUALIFICATION_WORK_RULES,
            *GRAPHIC_AND_DEMONSTRATION_MATERIAL_RULES,
            *PROJECT_DESIGNATION_RULES,
        ),
    ),
    "small_written_works": _profile(
        "small_written_works",
        "Referat / Control Work / Calculation-Graphic Work / Essay",
        (_SMALL_WRITTEN_DOC,),
        SMALL_WRITTEN_WORK_RULES,
    ),
    "graphic_and_demonstration_materials": _profile(
        "graphic_and_demonstration_materials",
        "Graphic and Demonstration Materials",
        (_GRAPHIC_DOC,),
        GRAPHIC_AND_DEMONSTRATION_MATERIAL_RULES,
    ),
    "project_designations": _profile(
        "project_designations",
        "Project Designations",
        (_PROJECT_DESIGNATION_DOC,),
        PROJECT_DESIGNATION_RULES,
    ),
}
