---
name: sfu-practice
description: Use for SFU practice reports — отчёт по практике, учебная/производственная/преддипломная практика, отчёт о практике (profile practice_reports). Trigger on "практика", "отчёт по практике", "производственная практика", "учебная практика", "преддипломная", "practice report SFU". Produces V2 TXT with Введение / задачи практики / выполненные работы / Заключение, then defers to sfu-common.
---

# Отчёт по практике — SFU

profile: `practice_reports`. Load **sfu-common** for syntax, lint, and conversion.

## 1. Структура заголовков (heading skeleton — start here)

```text
[DOC syntax=2 profile=practice_reports language=ru]
[META key=title value="Отчёт по <тип> практике"]
[META key=student value="<ФИО>"]
[META key=group value="<ГРУППА>"]
[META key=supervisor value="<ФИО руководителя практики>"]
[META key=discipline value="<Тип практики и период>"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # титульный лист берётся из шаблона; встроенная генерация в разработке

[STRUCTURAL title="ВВЕДЕНИЕ"]
[P] <Место практики, сроки, цель и индивидуальное задание.>

[H level=1 title="Задачи практики" number=auto]
[LIST type=numbered]
[1)] <Задача 1.>
[2)] <Задача 2.>
[LIST_END]

[H level=1 title="<Выполненные работы>" number=auto]
[H level=2 title="<сгенерированный этап/задание>" number=auto]   # 2.1 (≥2 each)
[P] <Что сделано, как, с какими результатами.>
[H level=2 title="<сгенерированный этап/задание>" number=auto]   # 2.2
[P] <…>

[STRUCTURAL title="ЗАКЛЮЧЕНИЕ"]
[P] <Итоги практики, приобретённые навыки и компетенции.>

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]   # if sources cited
[SOURCE number=1] <Источник.>
```

«Введение», «Заключение», «Список использованных источников» are structural. «Задачи практики» and
«Выполненные работы» are level-1; the works section needs ≥2 level-2 subsections.

## 2. Спросить перед написанием первых разделов (always)

Gather metadata first, especially **место и период практики** (never invent). Then ask **once**:

> «Содержание Введения и Задач практики укажете сами или сгенерировать?»
> - **Вариант A** — пользователь даёт текст.
> - **Вариант B** — генерируешь из задания.

Titles and body of «Выполненные работы» — **always agent-generated**.

## 3. Дальше

Follow **sfu-common**: write `.txt`, `lint --format json` (fix error/fatal only), then
`convert --format json` **with a template** — `--template <path> --skip-generated-front-matter` is
the default (ask the user: default `templates/template1.docx` or their own). Built-in title-page/ToC
generation is in active development; `--strict` / `--validate-output` are advisory — see
`../../references/cli.md`. Syntax → `../../references/v2-syntax.md`.
