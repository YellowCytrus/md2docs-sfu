# Diagnostics — codes & fixes

Run `lint` (or `convert`) with `--format json` and read the `diagnostics` array. Each entry has a
`code`, `severity` (`info` | `warning` | `error` | `fatal`), and source location.

## Exit codes

| Code | Meaning                          |
|------|----------------------------------|
| 0    | No error-severity diagnostics    |
| 1    | Warnings present (only under `--strict`) |
| 2    | Errors present                   |

**Gate on error/fatal severity from plain `lint`.** Warnings are advisory. Do **not** make
`--strict` a pass/fail gate: it promotes `FORMAT_RULE_NOT_SUPPORTED` warnings (unimplemented
converter rules) to errors you can't fix in TXT. Likewise `--validate-output` currently emits false
positives like `FORMAT_INDENT` on list items. See `references/cli.md`.

## Syntax codes (parser)

| Code                       | Fix                                                        |
|----------------------------|------------------------------------------------------------|
| `TXT_UNKNOWN_MARKER`       | Wrap the line in `[P]` or correct the marker spelling.     |
| `TXT_CYRILLIC_IN_MARKER`   | Replace Cyrillic letter with its Latin twin (`Н`→`H`, `Т`→`T`, `Р`→`P`). |
| `TXT_MISSING_BLOCK_END`    | Add the matching `[*_END]` / `[/…]`.                       |
| `TXT_DUPLICATE_ID`         | Make ids unique (`fig:arch1`, `fig:arch2`).               |
| `TXT_INVALID_TABLE_SHAPE`  | Pad/trim the row so all rows have equal `\|`-cell count.   |
| `TXT_MALFORMED_ATTRIBUTE`  | Quote values with spaces; check `key=value`; add missing required attr. |
| `TXT_UNSUPPORTED_SYNTAX`   | Put `syntax=2` in `[DOC]`.                                 |
| `INVALID_HEADING_LEVEL`    | Use level 1–4 only.                                        |
| `HEADING_LEVEL_SKIPPED`    | Don't jump levels (1 → 3); go 1 → 2 → 3.                   |
| `TXT_IMAGE_NOT_FOUND`      | Fix `src=` path (resolved under the `images` folder).      |

## Structure / formatting codes (validator)

| Code                                  | Fix                                                |
|---------------------------------------|----------------------------------------------------|
| `TXT_MISSING_METADATA`                | Add the `[META]` field the profile requires (see `references/metadata.md`). |
| `STRUCTURE_TITLE_PAGE_MISSING`        | Add `[TITLE_PAGE]` or use a template / `--skip-generated-front-matter`. |
| `STRUCTURE_REQUIRED_SECTION_MISSING`  | Add the required structural section for the profile. |
| `STRUCTURE_SECTION_OUT_OF_ORDER`      | Reorder: front-matter → main → ЗАКЛЮЧЕНИЕ → СПИСОК ИСТОЧНИКОВ → приложения. |
| `STRUCTURE_APPENDIX_BEFORE_SOURCES`   | Move appendices after the bibliography.            |
| `HEADING_POINT_REQUIRES_SUBPOINTS`    | A subdivided heading needs ≥2 sub-points (give 4.1 **and** 4.2). |
| `FIGURE_NEVER_REFERENCED`             | Add `[REF target=<fig id>]` in the text.           |
| `REFERENCE_UNRESOLVED`                | The `target` id doesn't exist — define it or fix the id. |
| `BIBLIOGRAPHY_MISSING_FIELD`          | Add the required field for that `[SOURCE type=…]`. |
| `FOOTNOTE_UNMATCHED_ANCHOR` / `_BODY` | Pair each `[FN_ANCHOR]` with a `[FN_BODY]` (same id). |
| `PROJECT_DESIGNATION_FORMAT`          | Fix the `[DESIGNATION …]` code format.             |

Prefixes by area: `TXT_` syntax · `STRUCTURE_` composition · `FORMAT_`/`STYLE_` layout ·
`HEADING_` `FIGURE_` `FORMULA_` `TABLE_` `BIBLIOGRAPHY_` `CITATION_` `FOOTNOTE_` `REFERENCE_`
`APPENDIX_` `PROJECT_DESIGNATION_` `GRAPHIC_` `POSTER_` `SLIDE_` `TOC_`.

## Advisory diagnostics (don't block; act only if you can)

| Code                            | What to do                                                   |
|---------------------------------|--------------------------------------------------------------|
| `FORMAT_RULE_NOT_SUPPORTED`     | Converter limitation — ignore (only an "error" under `--strict`). |
| `FORMAT_INDENT` (lists, `--validate-output`) | Known renderer/validator mismatch — ignore.     |
| `STRUCTURE_TITLE_PAGE_MISSING`  | Add `[TITLE_PAGE]` after the `[META]` block (or use `--template … --skip-generated-front-matter`). |
| `STYLE_ABBREVIATION_NOT_INTRODUCED` | Introduce the abbreviation on first use, or add an `[ABBREVIATIONS]` block. Optional. |

## Cyrillic-in-markers helpers

```bash
python -m sfu_converter.tools.check_cyrillic_markers
python -m sfu_converter.tools.fix_cyrillic_markers
```
