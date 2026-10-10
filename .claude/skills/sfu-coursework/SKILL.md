---
name: sfu-coursework
description: Use for SFU coursework — курсовая работа, курсовой проект (profile coursework). Trigger on "курсовая", "курсовой проект", "курсач", "coursework SFU". Produces V2 TXT with Введение / аналитическая + проектная главы / Заключение / Список источников / Приложения, then defers to sfu-common for lint + convert.
---

# Курсовая работа / курсовой проект — SFU

profile: `coursework`. Load **sfu-common** for syntax, lint, and conversion. This skill owns the
heading structure and the opening-content question.

## 1. Структура заголовков (heading skeleton — start here)

```text
[DOC syntax=2 profile=coursework language=ru]
[META key=title value="<ТЕМА>"]
[META key=student value="<ФИО>"]
[META key=group value="<ГРУППА>"]
[META key=supervisor value="<ФИО руководителя>"]
[META key=discipline value="<Дисциплина>"]
[META key=department value="<Кафедра>"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # титульный лист берётся из шаблона; встроенная генерация в разработке

[STRUCTURAL title="ВВЕДЕНИЕ"]
[P] <Актуальность, цель, задачи, объект, предмет, методы.>

[H level=1 title="<Аналитическая глава>" number=auto]
[H level=2 title="<сгенерированный раздел>" number=auto]   # 1.1 (≥2 per chapter)
[P] <Обзор предметной области.>
[H level=2 title="<сгенерированный раздел>" number=auto]   # 1.2
[P] <…>

[H level=1 title="<Проектная глава>" number=auto]
[H level=2 title="<сгенерированный раздел>" number=auto]   # 2.1
[FIGURE src="arch.png" caption="Архитектура решения" id=fig:arch]
[P] См. рисунок [REF target=fig:arch].
[H level=2 title="<сгенерированный раздел>" number=auto]   # 2.2

[STRUCTURAL title="ЗАКЛЮЧЕНИЕ"]
[P] <Итоги, выводы по задачам.>

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1] <Источник.>

[PAGE_BREAK]
[APPENDIX id=app:a letter="А" title="ПРИЛОЖЕНИЕ А" type="справочное"]   # optional
[P] <Листинги / схемы.>
```

«Введение», «Заключение», «Список использованных источников» are structural (no number, new page).
Main chapters are level-1 (`number=auto`), with ≥2 level-2 subsections each. Appendices come **after**
the bibliography.

## 2. Спросить перед написанием Введения (always)

Gather metadata first (never invent ФИО / group / supervisor). Then ask **once**:

> «Содержание Введения (актуальность, цель, задачи) укажете сами или сгенерировать из темы?»
> - **Вариант A** — пользователь даёт текст.
> - **Вариант B** — генерируешь из темы.

Chapter titles and body of the аналитическая/проектная главы — **always agent-generated**.

## 3. Дальше

Follow **sfu-common**: write `.txt`, `lint --format json` (fix error/fatal only), then
`convert --format json` **with a template** — `--template <path> --skip-generated-front-matter` is
the default (ask the user: default `templates/template1.docx` or their own). Built-in title-page/ToC
generation is in active development; `--strict` / `--validate-output` are advisory — see
`../../references/cli.md`. Coursework often needs a `[DESIGNATION]` project code — see
`../../references/v2-syntax.md` (advanced).
