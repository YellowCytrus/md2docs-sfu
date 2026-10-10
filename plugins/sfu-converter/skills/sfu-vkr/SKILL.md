---
name: sfu-vkr
description: Use for SFU graduation qualification work — ВКР, выпускная квалификационная работа, бакалаврская/дипломная работа, магистерская диссертация, дипломный проект (profile graduation_qualification_work). Trigger on "ВКР", "выпускная", "диплом", "дипломная работа", "магистерская диссертация", "VKR SFU". Produces V2 TXT with Реферат / Введение / главы / Заключение / Список источников / Приложения, then defers to sfu-common.
---

# Выпускная квалификационная работа (ВКР) — SFU

profile: `graduation_qualification_work`. Load **sfu-common** for syntax, lint, and conversion.
The largest SFU document — title page + ToC are usually supplied via a DOCX template.

## 1. Структура заголовков (heading skeleton — start here)

```text
[DOC syntax=2 profile=graduation_qualification_work language=ru]
[META key=title value="<ТЕМА ВКР>"]
[META key=student value="<ФИО>"]
[META key=group value="<ГРУППА>"]
[META key=supervisor value="<ФИО руководителя>"]
[META key=department value="<Кафедра>"]
[META key=institute value="<Институт>"]
[META key=city value="Красноярск"]
[META key=year value="2025"]

[TITLE_PAGE]   # титульный лист берётся из шаблона; встроенная генерация в разработке

[STRUCTURAL title="РЕФЕРАТ"]
[P] <Объём, ключевые слова, объект, цель, результаты, область применения.>

[STRUCTURAL title="ВВЕДЕНИЕ"]
[P] <Актуальность, цель, задачи, объект, предмет, научная новизна, практическая значимость.>

[H level=1 title="<Глава 1 — теоретическая>" number=auto]
[H level=2 title="<сгенерированный раздел>" number=auto]   # 1.1 (≥2 per chapter)
[P] <…>
[H level=2 title="<сгенерированный раздел>" number=auto]   # 1.2

[H level=1 title="<Глава 2 — проектная/практическая>" number=auto]
[H level=2 title="<сгенерированный раздел>" number=auto]   # 2.1
[P] <…>
[H level=2 title="<сгенерированный раздел>" number=auto]   # 2.2

[STRUCTURAL title="ЗАКЛЮЧЕНИЕ"]
[P] <Выводы по каждой задаче, достигнутые результаты.>

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1 type=normative lang=ru]
title="СТУ 7.5-07-2021 …" city="Красноярск" publisher="СФУ" year=2021
[/SOURCE]

[PAGE_BREAK]
[APPENDIX id=app:a letter="А" title="ПРИЛОЖЕНИЕ А" type="обязательное"]
[P] <Листинги, схемы, акты внедрения.>
```

«Реферат», «Введение», «Заключение», «Список использованных источников» are structural. Two or
more numbered chapters, each with ≥2 level-2 subsections. Appendices after the bibliography.

## 2. Спросить перед написанием Введения/Реферата (always)

Gather metadata first (never invent ФИО / group / supervisor / кафедра). Then ask **once**:

> «Содержание Введения и Реферата (цель, задачи, новизна) укажете сами или сгенерировать?»
> - **Вариант A** — пользователь даёт текст.
> - **Вариант B** — генерируешь из темы.

Chapter titles and body — **always agent-generated**.

## 3. Дальше

Follow **sfu-common**: write `.txt`, `lint --format json` (fix error/fatal only), then
`convert --format json` **with a template** — `--template <path> --skip-generated-front-matter` is
the default (ask the user: default `templates/template1.docx` or their own). The template supplies
the official title page + ToC; built-in generation is in active development. `--strict` /
`--validate-output` are advisory — see `../../references/cli.md`. A `[DESIGNATION]` project code is
often required — see `../../references/v2-syntax.md` (advanced).
