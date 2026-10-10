---
name: sfu-research
description: Use for SFU research-work reports — отчёт о НИР, научно-исследовательская работа, отчёт о научно-исследовательской работе магистранта (profile research_reports). Trigger on "НИР", "отчёт по НИР", "научно-исследовательская работа", "research report SFU". Produces V2 TXT with Реферат / Введение / разделы НИР / Заключение / Список источников, then defers to sfu-common.
---

# Отчёт о научно-исследовательской работе (НИР) — SFU

profile: `research_reports`. Load **sfu-common** for syntax, lint, and conversion.

## 1. Структура заголовков (heading skeleton — start here)

```text
[DOC syntax=2 profile=research_reports language=ru]
[META key=title value="<ТЕМА НИР>"]
[META key=student value="<ФИО>"]
[META key=group value="<ГРУППА>"]
[META key=supervisor value="<ФИО руководителя>"]
[META key=department value="<Кафедра>"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # титульный лист берётся из шаблона; встроенная генерация в разработке

[STRUCTURAL title="РЕФЕРАТ"]
[P] <Объём, ключевые слова, цель, методы, результаты.>

[STRUCTURAL title="ВВЕДЕНИЕ"]
[P] <Актуальность, цель и задачи исследования, объект, предмет, методология.>

[H level=1 title="<Раздел — обзор/состояние вопроса>" number=auto]
[H level=2 title="<сгенерированный подраздел>" number=auto]   # 1.1 (≥2 each)
[P] <…>
[H level=2 title="<сгенерированный подраздел>" number=auto]   # 1.2

[H level=1 title="<Раздел — методика и результаты>" number=auto]
[H level=2 title="<сгенерированный подраздел>" number=auto]   # 2.1
[FORMULA id=eq:main number=auto]
<формула>
[FORMULA_END]
[H level=2 title="<сгенерированный подраздел>" number=auto]   # 2.2

[STRUCTURAL title="ЗАКЛЮЧЕНИЕ"]
[P] <Основные результаты и выводы исследования.>

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1] <Источник.>
```

«Реферат», «Введение», «Заключение», «Список использованных источников» are structural. Numbered
research sections at level-1, ≥2 level-2 subsections each.

## 2. Спросить перед написанием Введения (always)

Gather metadata first (never invent ФИО / group / supervisor). Then ask **once**:

> «Содержание Введения (цель, задачи, методология) укажете сами или сгенерировать?»
> - **Вариант A** — пользователь даёт текст.
> - **Вариант B** — генерируешь из темы.

Section titles and body — **always agent-generated**.

## 3. Дальше

Follow **sfu-common**: write `.txt`, `lint --format json` (fix error/fatal only), then
`convert --format json` **with a template** — `--template <path> --skip-generated-front-matter` is
the default (ask the user: default `templates/template1.docx` or their own). Built-in title-page/ToC
generation is in active development; `--strict` / `--validate-output` are advisory — see
`../../references/cli.md`. Syntax → `../../references/v2-syntax.md`.
