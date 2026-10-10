---
name: sfu-report-lab
description: Use for the DEFAULT SFU report — лабораторная работа, отчёт по лабораторной работе, практическая работа, проектная работа (profile lab_practical_project_reports). Trigger on "лаба", "лабораторная №N", "отчёт по практической работе", "проектное задание", "lab report SFU". Produces V2 TXT with the standard Цель / Задачи / Ход работы structure, then defers to sfu-common for lint + convert.
---

# Лабораторная / практическая / проектная работа — SFU

profile: `lab_practical_project_reports` · the most common SFU document. Load **sfu-common** for
syntax, lint, and conversion. This skill owns the heading structure and the opening-content question.

## 1. Структура заголовков (heading skeleton — start here)

```text
[DOC syntax=2 profile=lab_practical_project_reports language=ru]
[META key=document_type value="Отчёт по лабораторной работе"]
[META key=title value="Лабораторная работа №<N>: <ТЕМА>"]
[META key=student value="<ФИО>"]
[META key=group value="<ГРУППА>"]
[META key=teacher value="<ФИО преподавателя>"]
[META key=discipline value="<Дисциплина>"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # титульный лист берётся из шаблона; встроенная генерация в разработке

[H level=1 title="Цель" number=auto]
[P] <Цель работы.>

[H level=1 title="Задачи" number=auto]
[LIST type=numbered]
[1)] <Задача 1.>
[2)] <Задача 2.>
[LIST_END]

[H level=1 title="Описание варианта задания" number=auto]   # OPTIONAL — drop if no variant
[P] <Условие варианта / индивидуального задания.>

[H level=1 title="Ход работы" number=auto]
[H level=2 title="<сгенерированный заголовок этапа>" number=auto]   # 4.1
[P] <Описание этапа + объекты (таблицы/рисунки/листинги).>
[H level=2 title="<сгенерированный заголовок этапа>" number=auto]   # 4.2 (always ≥2 sub-points)
[P] <Описание этапа.>

[H level=1 title="Заключение" number=auto]            # recommended add-on
[P] <Итоги, что достигнуто.>

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]  # add only if sources are cited
[SOURCE number=1] <Источник.>
```

Rules: «Цель», «Задачи», «Описание варианта задания» are level-1 (`number=auto` → 1, 2, 3).
«Ход работы» subsections are level-2 → render 4.1 / 4.2. Always give **≥2** subsections under
«Ход работы» (`HEADING_POINT_REQUIRES_SUBPOINTS`). «Описание варианта задания» is optional.

## 2. Спросить перед написанием первых разделов (always)

First gather metadata (для lab обязательны `document_type`, `title`, `student`, `group`, `teacher`
— never invent). Then ask **once**:

> «Содержание разделов Цель, Задачи (и Описание варианта задания) укажете сами или сгенерировать из темы?»
> - **Вариант A** — пользователь даёт текст; вставляешь как есть.
> - **Вариант B** — генерируешь из темы и условий.

«Ход работы» — заголовки этапов и их содержание **всегда генерируешь сам**. If the user already
supplied the opening content, skip the question.

## 3. Дальше

Follow **sfu-common**: write the `.txt`, `lint --format json` (fix error/fatal only), then
`convert --format json` **with a template** — `--template <path> --skip-generated-front-matter` is
the default (ask the user: default `templates/template1.docx` or their own). Built-in title-page/ToC
generation is in active development. Don't use `--strict` / `--validate-output` as gates (advisory
only — see `../../references/cli.md`). Syntax → `../../references/v2-syntax.md`.
