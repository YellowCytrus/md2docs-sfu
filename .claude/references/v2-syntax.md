# V2 TXT syntax — condensed reference

Authoritative source: `docs/v2-*.md` in the repo. This is the agent-facing crib sheet.

## Hard rules (never break)

1. **Latin uppercase markers only.** `[H]` not `[Н]`, `[TABLE]` not `[ТABLE]`, `[P]` not `[Р]`.
   Cyrillic lookalikes (`Н Т Р Е А С О В М К`) break parsing → `TXT_CYRILLIC_IN_MARKER`.
2. **First non-empty line is `[DOC syntax=2 …]`.** Anything else → `TXT_UNSUPPORTED_SYNTAX`.
3. **Every body line is wrapped in a marker.** Bare prose → `TXT_UNKNOWN_MARKER`
   (warning, error under `--strict`). Normal text goes in `[P] …`.
4. **Close every paired block:** `[TABLE]`→`[TABLE_END]`, `[LIST]`→`[LIST_END]`,
   `[FORMULA]`→`[FORMULA_END]`, `[RAW]`→`[RAW_END]`, `[SOURCE …type=…]`→`[/SOURCE]`,
   `[SECTION]`→`[/SECTION]`, `[FN_BODY]`→`[/FN_BODY]`. Missing → `TXT_MISSING_BLOCK_END`.
5. **Unique ids** across figures/tables/formulas/appendices → else `TXT_DUPLICATE_ID`.
6. **Heading levels 1–4 only** → else `INVALID_HEADING_LEVEL`.
7. **Quote attribute values with spaces/Cyrillic:** `title="Ход работы"`.
8. **Never invent** ФИО, group, supervisor, dates — ask the user.

## Document declaration & metadata

```text
[DOC syntax=2 profile=<PROFILE> language=ru]
[META key=title value="Отчёт по лабораторной работе"]
[META key=student value="Иванов И. И."]
[META key=group value="КИ22-01"]
[META key=supervisor value="Петров А. В."]
[META key=city value="Красноярск"]
[META key=year value="2025"]
```

`[DOC]` is mandatory and first. Required `[META]` keys depend on profile → `references/metadata.md`.

## Text

```text
[H level=1 title="Ход работы" number=auto]    # numbered heading, level 1–4; number=auto → 1, 1.1, 1.2…
[STRUCTURAL title="ВВЕДЕНИЕ"]                  # special section (no number, new page, centered)
[P] Обычный абзац. Поддерживает **полужирный** и *курсив*.
[P role=example] Абзац со специальной ролью.
```

Recognized structural titles: `РЕФЕРАТ`, `АННОТАЦИЯ`, `СОДЕРЖАНИЕ`, `ВВЕДЕНИЕ`, `ЗАКЛЮЧЕНИЕ`,
`СПИСОК СОКРАЩЕНИЙ`, `СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ`. An `[H level=1]` with the same title is
auto-recognized too, but explicit `[STRUCTURAL]` is clearer.

Quality rule: a heading point that is subdivided needs **≥2** sub-points of the same level
(`HEADING_POINT_REQUIRES_SUBPOINTS`). So `Ход работы` → at least 4.1 **and** 4.2.

## Escaping literal brackets

```text
[RAW]
def f(x):
    return x[0]        # square brackets here are NOT parsed as markers
[RAW_END]
```

Always wrap code / anything containing `[...]` in `[RAW]…[RAW_END]`.

## Objects

```text
[FIGURE src="arch.png" caption="Архитектура системы" id=fig:arch]      # auto «Рисунок N — …»
[P] См. рисунок [REF target=fig:arch].                                  # reference it (else FIGURE_NEVER_REFERENCED)

[TABLE caption="Методы HTTP" id=tbl:http]
| Метод | Описание          |
| GET   | Получение ресурса |
| POST  | Создание ресурса  |
[TABLE_END]
# first row = header (unless header=false). Equal cell count per row → else TXT_INVALID_TABLE_SHAPE.

[LIST type=numbered]            # type ∈ bullet | numbered | lettered
[1)] Первый шаг.               # item markers: [-] [1)] [а)]
[2)] Второй шаг.
[LIST_END]

[FORMULA id=eq:rmse number=auto]
RMSE = sqrt(sum((y_i - y_pred_i)^2) / n)
[FORMULA_SYMBOL name=n text="размер выборки"]
[FORMULA_END]
[FORMULA_EXPLANATION] где y_i — факт, y_pred_i — прогноз, n — размер выборки
```

## References, footnotes, sources

```text
[REF target=fig:arch]    [REF target=tbl:http]    [REF target=source:1]

[P] Текст с пояснением [FN id=1 text="Текст сноски."].

[STRUCTURAL title="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"]
[SOURCE number=1] Петров А. В. Машинное обучение. — М.: Наука, 2023.
[SOURCE number=2 type=article lang=ru]
authors="Петров П. П., Сидоров С. С." title="Проверка документов"
journal="Вестник СФУ" year=2022 number=4 pages=12-18
[/SOURCE]
```

GOST `type` values: `normative`, `patent`, `book_one_author`, `book_two_authors`,
`book_three_authors`, `book_four_plus_authors`, `volume`, `dissertation`, `article`, `electronic`.
Free-text `[SOURCE number=N] …` is fine when you don't need structured GOST assembly.

## Appendices & page breaks

```text
[PAGE_BREAK]
[APPENDIX id=app:a letter="А" title="ПРИЛОЖЕНИЕ А" type="справочное"]
[P] Листинг 1 — реализация модуля.
[RAW]
def authorize(user):
    return user.token is not None
[RAW_END]
```

Appendices come **after** the bibliography (else `STRUCTURE_APPENDIX_BEFORE_SOURCES`).

## Advanced (rarely needed for ordinary reports)

`[ABBREVIATIONS]…[ABBREVIATIONS_END]` (with `[ABBR short=… long=…]`), `[DESIGNATION …]`
(project codes), `[SECTION …]…[/SECTION]` (landscape / custom sheet & frame), `[DRAWING …]`,
`[POSTER …]`, `[SLIDE_DECK]/[SLIDE]` (PPTX export). See `docs/v2-extensions.md`.
