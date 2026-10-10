---
name: sfu-small-works
description: Use for small SFU written works — реферат, контрольная работа, расчётно-графическое задание (РГЗ), расчётное задание, эссе (profile small_written_works). Trigger on "реферат", "контрольная", "контрольная работа", "РГЗ", "расчётно-графическое", "эссе", "essay SFU". Produces a lighter V2 TXT structure, then defers to sfu-common.
---

# Реферат / контрольная / РГЗ / эссе — SFU

profile: `small_written_works`. Load **sfu-common** for syntax, lint, and conversion. Lighter title
page and structure than a full report.

## 1. Структура заголовков (heading skeleton — start here)

```text
[DOC syntax=2 profile=small_written_works language=ru]
[META key=title value="<ТЕМА>"]
[META key=student value="<ФИО>"]
[META key=group value="<ГРУППА>"]
[META key=discipline value="<Дисциплина>"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # титульный лист берётся из шаблона; встроенная генерация в разработке

[STRUCTURAL title="ВВЕДЕНИЕ"]                         # for реферат / эссе
[P] <Постановка вопроса, цель работы.>

[H level=1 title="<сгенерированный раздел>" number=auto]   # 1
[P] <Содержательный текст.>
[H level=1 title="<сгенерированный раздел>" number=auto]   # 2
[P] <…>

[STRUCTURAL title="ЗАКЛЮЧЕНИЕ"]
[P] <Выводы.>

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1] <Источник.>
```

Variants:
- **Реферат / эссе** — Введение → 2–4 numbered sections → Заключение → Список источников.
- **Контрольная / расчётное задание** — numbered tasks: `[H level=1 title="Задача N" number=auto]`
  with `[FORMULA]` blocks and `[P]` solutions; Введение/Заключение optional.
- **РГЗ** — calculation sections with `[FORMULA]` + `[TABLE]`; add `[FIGURE]` for графики.

## 2. Спросить перед написанием (always)

Gather metadata first (never invent ФИО / group). Then ask **once**:

> «Содержание первых разделов (Введение / условия задач) укажете сами или сгенерировать из темы?»
> - **Вариант A** — пользователь даёт текст / условия.
> - **Вариант B** — генерируешь из темы.

Section titles and body — **always agent-generated** (for контрольная, use the task conditions the
user provides verbatim).

## 3. Дальше

Follow **sfu-common**: write `.txt`, `lint --format json` (fix error/fatal only), then
`convert --format json` **with a template** — `--template <path> --skip-generated-front-matter` is
the default (ask the user: default `templates/template1.docx` or their own). Built-in title-page/ToC
generation is in active development; `--strict` / `--validate-output` are advisory — see
`../../references/cli.md`. Syntax → `../../references/v2-syntax.md`.
