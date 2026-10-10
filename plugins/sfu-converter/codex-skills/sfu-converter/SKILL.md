---
name: sfu-converter
description: Use for any Siberian Federal University (СФУ/SFU) academic document request: лабораторная, практическая, проектная, практика, НИР, курсовая, ВКР, диплом, реферат, контрольная, РГЗ, эссе, or converting/linting SFU V2 TXT to DOCX. Single Codex entry point that routes to the right profile and runs the sfu-converter lint→fix→convert workflow.
---

# SFU Converter

Single Codex entry point. Do not ask the user to invoke separate SFU skills. Use this skill for all
SFU document generation, linting, fixing, and conversion tasks.

## Load References

Read only the files needed for the requested document type:

- Common workflow and V2 syntax: `../../skills/sfu-common/SKILL.md`
- Лабораторная / практическая / проектная: `../../skills/sfu-report-lab/SKILL.md`
- Курсовая / курсовой проект: `../../skills/sfu-coursework/SKILL.md`
- ВКР / диплом / магистерская диссертация: `../../skills/sfu-vkr/SKILL.md`
- НИР / научно-исследовательская работа: `../../skills/sfu-research/SKILL.md`
- Отчёт по практике: `../../skills/sfu-practice/SKILL.md`
- Реферат / контрольная / РГЗ / эссе: `../../skills/sfu-small-works/SKILL.md`

## Operating Rules

1. Gather required metadata. Never invent ФИО, group, teacher/supervisor, or dates.
2. Pick the profile from the user request; if unclear, use `common` and explain the assumption.
3. Ask once whether the user provides opening sections or you generate them from the topic, unless
   that text was already supplied.
4. Generate V2 TXT with Latin uppercase markers only and no bare prose.
5. Run `sfu-converter lint --format json`; fix error/fatal diagnostics and re-lint up to five times.
6. Ask once whether to use `templates/template1.docx` or a custom template before conversion.
7. Convert with `--skip-generated-front-matter --format json` and report DOCX path, profile,
   template, error/warning counts, and residual warnings.

Use the referenced profile file for the heading skeleton and the common file for exact syntax,
metadata requirements, diagnostics, and CLI command details.
