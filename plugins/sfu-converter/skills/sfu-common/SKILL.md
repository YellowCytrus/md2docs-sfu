---
name: sfu-common
description: Shared rules for generating any SFU (Сибирский Федеральный Университет / СФУ) academic document in V2 TXT syntax and converting to DOCX via the sfu-converter CLI. Loaded together with a profile skill (sfu-report-lab, sfu-coursework, sfu-vkr, sfu-research, sfu-practice, sfu-small-works). Also handles generic "convert this TXT to DOCX SFU style" / "lint my SFU report" when no specific document type is named. Covers V2 syntax, the lint→fix→convert loop, diagnostics, metadata, and bibliography.
---

# SFU Converter — common requirements

Foundation skill. A profile skill picks the **heading structure** and **required metadata**; this
skill supplies the **syntax, workflow, and fixes** they all share. If the user names a document type
(лабораторная / курсовая / ВКР / НИР / практика / реферат), the matching profile skill also loads —
follow its heading skeleton, then come back here for syntax + conversion.

## Workflow

```
[gather metadata] → [pick profile] → [ask: who writes first sections] → [write V2 TXT] → [lint] → [fix errors] → [ask: which template] → [convert with template] → [report]
```

1. **Gather metadata** — `title`, `student` (ФИО), `group`, `year` at minimum; `supervisor`,
   `city=Красноярск`, `discipline` recommended. Never invent them — ask once.
   Full table → `../../references/metadata.md`.
2. **Pick profile** (table below) and put it in `[DOC syntax=2 profile=<P> language=ru]`.
3. **Ask the content question** (see next section) before writing Цель / Задачи / Описание.
4. **Write the `.txt`** in V2 syntax → `../../references/v2-syntax.md`. Keep `[TITLE_PAGE]` +
   `[META]`, but note the title page + ToC come from a **template** (built-in generation is in
   active development — skipped by default).
5. **Lint** (`lint --format json`, no `--strict`), parse JSON diagnostics, fix **error/fatal**
   only, repeat (≤5) → `../../references/cli.md`, `../../references/diagnostics.md`.
6. **Convert** (`convert --format json`) **with a template** — the default mode. Ask the user once
   «использовать шаблон по умолчанию `templates/template1.docx` или укажете свой?», then run
   `convert … --template <path> --skip-generated-front-matter`. Built-in title-page/ToC generation
   is in active development and skipped by default. `--strict` / `--validate-output` are advisory —
   don't use them as gates (see cli.md).
7. **Report** DOCX path, profile, template used, error/warning counts, residual warnings.

## The content question (always ask, every document)

Before writing the opening sections (Цель / Задачи / Описание варианта задания), ask **once**:

> «Содержание первых разделов (Цель, Задачи, описание задания) укажете сами или сгенерировать из темы?»
> - **Вариант A** — пользователь даёт текст; вставляешь как есть, только оформляешь.
> - **Вариант B** — генерируешь из темы и условий работы.

Titles **and** content inside «Ход работы» (and any main chapters) are **always agent-generated** —
don't ask for those. If the user already provided the opening content in their message, skip the
question and use it.

## Profile selection

| User says                                | Profile                          | Skill            |
|------------------------------------------|----------------------------------|------------------|
| «лабораторная», «практическая», «проектная» | `lab_practical_project_reports` | sfu-report-lab   |
| «отчёт по практике»                      | `practice_reports`               | sfu-practice     |
| «НИР», «научно-исследовательская»        | `research_reports`               | sfu-research     |
| «курсовая», «курсовой проект»            | `coursework`                     | sfu-coursework   |
| «ВКР», «выпускная квалификационная»      | `graduation_qualification_work`  | sfu-vkr          |
| «реферат», «контрольная», «РГЗ», «эссе»  | `small_written_works`            | sfu-small-works  |
| unsure                                   | `common`                         | —                |

Confirm names with `sfu-converter list-profiles --format json`.

## Hard rules (full list → references/v2-syntax.md)

1. Latin uppercase markers only — never Cyrillic twins (`Н Т Р Е А`).
2. First line `[DOC syntax=2 …]`.
3. Every body line wrapped in `[P]` (or another marker).
4. Close every block (`[TABLE_END]`, `[LIST_END]`, `[FORMULA_END]`, `[RAW_END]`, `[/SOURCE]`).
5. Unique ids; heading levels 1–4; quote attribute values with spaces.
6. A subdivided heading needs ≥2 sub-points (give 4.1 **and** 4.2, never a lone 4.1).
7. Code / literal `[...]` goes in `[RAW]…[RAW_END]`.
8. Never invent ФИО / group / supervisor / dates.

## Bibliography

```text
[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1] Петров А. В. Машинное обучение. — М.: Наука, 2023.
```

Numbered from 1, sequential. Use structured `[SOURCE type=…]…[/SOURCE]` for GOST assembly
(types in `../../references/v2-syntax.md`). Cite in text with `[REF target=source:1]`.

## Anti-patterns

- ❌ V1 syntax: `[H1]`, `[TABLE_START]`, `[IMAGE]`. V2 only.
- ❌ Bare prose without `[P]`.
- ❌ Cyrillic marker letters.
- ❌ Two objects sharing an `id`.
- ❌ Submitting un-linted TXT.
- ❌ Inventing metadata.

## References bundled with this plugin

- `../../references/v2-syntax.md` — markers, examples.
- `../../references/diagnostics.md` — codes + fixes.
- `../../references/cli.md` — commands + lint/convert loop.
- `../../references/metadata.md` — required `[META]` per profile.
