<!-- CANONICAL agent instructions. GEMINI.md is generated from this file via tools/sync_agent_docs.py — edit here, then run the script. -->

# SFU Converter — agent instructions

You generate Siberian Federal University (СФУ) academic documents in **V2 TXT syntax** for the
`sfu-converter` CLI, then **lint → fix → convert** them to DOCX per СТУ 7.5-07-2021. This file is the
portable rule set for CLI-capable agents (Codex, OpenCode, Antigravity, …). Claude Code users get the
richer multi-skill plugin instead — see `docs/installation.md`.

## Prerequisite

The CLI must be installed: `pipx install sfu-converter` (verify `sfu-converter --help`). In a dev
checkout without the console script, use `python -m sfu_converter.cli` with identical arguments.
Full per-agent setup → `docs/installation.md`.

## Workflow

```
gather metadata → pick profile → ask who writes the opening sections → write .txt
→ lint --format json → fix errors (≤5) → convert --format json → report
```

## Step 1 — Gather metadata (never invent)

Required `[META]` keys depend on the profile (missing → `TXT_MISSING_METADATA`):

| Profile                          | Required keys                                          |
|----------------------------------|--------------------------------------------------------|
| `lab_practical_project_reports`  | `document_type`, `title`, `student`, `group`, `teacher`|
| `practice_reports` / `research_reports` / `small_written_works` | `title`, `student`, `group`     |
| `coursework`                     | `title`, `student`, `group`, `supervisor`              |
| `graduation_qualification_work`  | `title`, `student`, `supervisor`                       |

`teacher` (преподаватель) vs `supervisor` (руководитель) are different keys — use the one the
profile asks for. Recommended extras: `city=Красноярск`, `discipline`, `year`. Add `[TITLE_PAGE]`
after the `[META]` block, but note it's **skipped by default**: the title page (and ToC) come from a
DOCX template (see Step 5–6) because built-in generation is in active development. Never fabricate
ФИО, group, teacher/supervisor, or dates — ask once.

## Step 2 — Pick profile

| User says                                   | profile=                          |
|---------------------------------------------|-----------------------------------|
| лабораторная / практическая / проектная     | `lab_practical_project_reports`   |
| отчёт по практике                           | `practice_reports`                |
| НИР / научно-исследовательская              | `research_reports`                |
| курсовая / курсовой проект                  | `coursework`                      |
| ВКР / диплом / магистерская диссертация      | `graduation_qualification_work`   |
| реферат / контрольная / РГЗ / эссе          | `small_written_works`             |
| unsure                                      | `common`                          |

Confirm with `sfu-converter list-profiles --format json`.

## Step 3 — Ask the content question (always, once)

> «Содержание первых разделов (Цель, Задачи, описание задания / Введение) укажете сами или
> сгенерировать из темы? Вариант A — даёте текст; Вариант B — генерирую я.»

Skip if the user already supplied that text. Titles **and** content inside «Ход работы» / main
chapters are **always agent-generated** — don't ask for those.

## Step 4 — Heading skeletons per profile

**Default report — `lab_practical_project_reports`:**

```text
[DOC syntax=2 profile=lab_practical_project_reports language=ru]
[META key=document_type value="Отчёт по лабораторной работе"]
[META key=title value="Лабораторная работа №N: Тема"]
[META key=student value="Иванов И. И."]
[META key=group value="КИ22-01"]
[META key=teacher value="Петров А. В."]
[META key=discipline value="Дисциплина"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # из шаблона; встроенная генерация в разработке (skipped by default)

[H level=1 title="Цель" number=auto]
[P] Текст цели.
[H level=1 title="Задачи" number=auto]
[LIST type=numbered]
[1)] Задача 1.
[2)] Задача 2.
[LIST_END]
[H level=1 title="Описание варианта задания" number=auto]   # optional
[P] Условие варианта.
[H level=1 title="Ход работы" number=auto]
[H level=2 title="Сгенерированный этап" number=auto]        # 4.1 (≥2 sub-points)
[P] Описание этапа.
[H level=2 title="Ещё этап" number=auto]                    # 4.2
[P] Описание этапа.
[H level=1 title="Заключение" number=auto]
[P] Итоги.
```

**coursework / graduation_qualification_work / research_reports / practice_reports** — use
structural sections and numbered chapters:

```text
[TITLE_PAGE]                            # after [META]; from template, generation in active development
[STRUCTURAL title="РЕФЕРАТ"]            # ВКР / НИР only
[STRUCTURAL title="ВВЕДЕНИЕ"]
[H level=1 title="Глава 1 …" number=auto]
[H level=2 title="Подраздел …" number=auto]   # ≥2 per chapter
[H level=2 title="Подраздел …" number=auto]
[H level=1 title="Глава 2 …" number=auto]
[H level=2 title="…" number=auto]
[H level=2 title="…" number=auto]
[STRUCTURAL title="ЗАКЛЮЧЕНИЕ"]
[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1] Источник.
[PAGE_BREAK]
[APPENDIX id=app:a letter="А" title="ПРИЛОЖЕНИЕ А" type="обязательное"]   # after sources
```

**small_written_works** — Введение → 2–4 numbered sections → Заключение → Список источников
(контрольная/РГЗ: numbered `Задача N` with `[FORMULA]`).

## Hard rules (breaking these fails parsing)

1. **Latin uppercase markers only** — never Cyrillic twins (`Н Т Р Е А С О В М К`).
2. First non-empty line is `[DOC syntax=2 profile=… language=ru]`.
3. Every body line wrapped in `[P]` (or another marker) — no bare prose.
4. Close every block: `[TABLE_END]`, `[LIST_END]`, `[FORMULA_END]`, `[RAW_END]`,
   `[/SOURCE]` (for `type=`), `[/SECTION]`, `[/FN_BODY]`.
5. Heading levels 1–4 only; quote values with spaces (`title="Ход работы"`).
6. A subdivided heading needs ≥2 sub-points (4.1 **and** 4.2).
7. Unique `id`s; reference each figure with `[REF target=fig:…]`.
8. Code / literal `[...]` inside `[RAW]…[RAW_END]`.
9. Tables: `|`-delimited, equal cell count, first row = header.
10. Never invent metadata.

## Markers (quick crib)

`[DOC]`, `[META key= value=]`, `[H level= title= number=auto]`, `[STRUCTURAL title=]`, `[P]`,
`[FIGURE src= caption= id=]`, `[TABLE caption= id=] … [TABLE_END]`,
`[LIST type=bullet|numbered|lettered] [-]/[1)]/[а)] … [LIST_END]`,
`[FORMULA id= number=auto] … [FORMULA_END]`, `[REF target=]`, `[SOURCE number=] …`,
`[FN id= text=]`, `[PAGE_BREAK]`, `[APPENDIX id= letter= title= type=]`, `[RAW] … [RAW_END]`.
Structural titles: РЕФЕРАТ, АННОТАЦИЯ, СОДЕРЖАНИЕ, ВВЕДЕНИЕ, ЗАКЛЮЧЕНИЕ, СПИСОК СОКРАЩЕНИЙ,
СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ.

## Step 5–6 — Lint, fix, convert

```bash
sfu-converter lint    --input report.txt --profile <P> --syntax-version 2 --format json
# parse JSON "diagnostics"; gate on severity error/fatal only → edit report.txt, re-lint (≤5 times)
sfu-converter convert --input report.txt --output report.docx \
  --profile <P> --syntax-version 2 \
  --template templates/template1.docx --skip-generated-front-matter --format json
```

**Front matter via template (default).** Built-in title-page + ToC generation is **not finished and
in active development** — it may not match СТУ 7.5-07. So the default convert ships the title page +
ToC from a DOCX template (`--template <path>`, a bare filename resolves against `templates/`) and
tells the converter to skip its own (`--skip-generated-front-matter`). **Ask the user once before
converting:** «использовать шаблон по умолчанию `templates/template1.docx` или укажете свой файл?»
Keep `[TITLE_PAGE]` + `[META]` in the `.txt` — `[TITLE_PAGE]` is a no-op under the skip flag and the
re-enable point once generation is ready.

> Do **not** add `--strict` or `--validate-output` as pass/fail gates. `--strict` turns
> `FORMAT_RULE_NOT_SUPPORTED` (unimplemented converter rules) into errors you can't fix in TXT;
> `--validate-output` emits false positives like `FORMAT_INDENT` on lists. They're advisory only.
> Warnings (abbreviation hints, etc.) don't block.

Common fixes: `TXT_UNKNOWN_MARKER` → wrap in `[P]`; `TXT_CYRILLIC_IN_MARKER` → Latinize the letter;
`TXT_MISSING_BLOCK_END` → add the `[*_END]`; `TXT_DUPLICATE_ID` → make ids unique;
`TXT_INVALID_TABLE_SHAPE` → equal cells; `TXT_MISSING_METADATA` → add the `[META]` field;
`HEADING_POINT_REQUIRES_SUBPOINTS` → add a second sub-point;
`STRUCTURE_APPENDIX_BEFORE_SOURCES` → move appendices after the bibliography.

## Step 7 — Report

DOCX path · profile · template used · error/warning counts · any residual warnings.

## Anti-patterns to refuse

V1 syntax (`[H1]`, `[TABLE_START]`, `[IMAGE]`); bare prose; Cyrillic markers; duplicate ids;
submitting un-linted TXT; inventing ФИО/group/supervisor/dates; plagiarized content.
