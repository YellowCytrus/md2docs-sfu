# CLI — commands & the lint→fix→convert loop

After `pipx install sfu-converter`, the command is `sfu-converter`. In a dev checkout without the
console script on PATH, use `python -m sfu_converter.cli` instead — identical arguments.

## Commands

| Command          | Purpose                                            |
|------------------|----------------------------------------------------|
| `convert`        | TXT → DOCX (or PPTX with `--output-format pptx`)   |
| `lint`           | Check syntax + profile rules, no output file       |
| `parse`          | Dump the AST as JSON                                |
| `validate-docx`  | Validate an existing DOCX against a profile         |
| `list-profiles`  | List formatting profiles                            |
| `explain-syntax` | Print syntax reference (`--syntax-version 2`)       |
| `export-coverage`| Standard-coverage matrix                            |

Common flags: `--syntax-version 2`, `--profile <name>`, `--format json` (machine-readable),
`--template <path>` + `--skip-generated-front-matter` (use a DOCX template that already has the
title page + ToC — **this is the default convert mode now**, see "Front matter via template"
below). Two stricter flags exist but are **advisory** — see the caveat below.

## The loop (what the agent runs)

```bash
# 1. Lint, machine-readable. Gate on ERROR/FATAL severity only.
sfu-converter lint  --input report.txt --profile <P> --syntax-version 2 --format json

# 2. If any diagnostic has severity error/fatal: parse JSON, edit report.txt, re-lint. Max ~5 iters.
#    Fix table → references/diagnostics.md. (warnings are advisory, don't block.)

# 3. Convert (produces the DOCX when there are no error-severity diagnostics).
#    Default: front matter (title page + ToC) comes from a DOCX template — see below.
sfu-converter convert --input report.txt --output report.docx \
  --profile <P> --syntax-version 2 \
  --template templates/template1.docx --skip-generated-front-matter --format json
```

## Front matter via template (default)

Built-in title-page + ToC generation is **not finished and in active development** — it may not
match СТУ 7.5-07. So the default convert ships the title page + ToC from a **DOCX template** and
tells the converter not to generate its own:

- `--template <path>` — a DOCX with the correct title page + ToC. A bare filename resolves against
  the project `templates/` dir (`--template templates/template1.docx`).
- `--skip-generated-front-matter` — skips the generated `[TITLE_PAGE]` + ToC blocks at render time.

**Ask the user once before converting:**

> «Использовать шаблон по умолчанию `templates/template1.docx` или укажете свой файл шаблона?»

Use the default template unless the user supplies their own path. Keep `[TITLE_PAGE]` + the full
`[META]` block in the `.txt` — required `[META]` still gates conversion, and `[TITLE_PAGE]` is the
re-enable point once built-in generation is ready (it's a no-op under `--skip-generated-front-matter`).

### Caveat: `--strict` and `--validate-output` are advisory, not gates

- `--strict` promotes **every** warning to an error — including `FORMAT_RULE_NOT_SUPPORTED`
  warnings, which are converter limitations (a rule the renderer/validator hasn't implemented yet).
  Those can't be fixed in the TXT, so `--strict` currently fails on valid documents. Use it only to
  audit style (e.g. abbreviation introduction), not as a pass/fail gate.
- `--validate-output` re-checks the rendered DOCX and currently reports false positives such as
  `FORMAT_INDENT` on list items (renderer vs validator disagree on list indent). Treat its findings
  as advisory.

So the default loop above uses **neither** flag and gates on error-severity diagnostics from plain
`lint`. Mention residual warnings to the user; don't loop forever trying to clear unfixable ones.

JSON shape (abridged):

```json
{ "ok": true, "command": "lint", "exit_code": 0,
  "diagnostics": [ { "code": "TXT_UNKNOWN_MARKER", "severity": "warning",
                     "line": 12, "message": "…" } ] }
```

Loop pseudocode:

```python
for _ in range(5):
    diags = json.loads(run("sfu-converter lint --format json …"))["diagnostics"]
    if not any(d["severity"] in ("error", "fatal") for d in diags):
        break
    apply_fixes(diags)          # only error/fatal; see references/diagnostics.md
else:
    raise RuntimeError("still has errors after 5 attempts")
# default convert: template supplies title page + ToC, no --strict / --validate-output (advisory only)
run("sfu-converter convert --template templates/template1.docx --skip-generated-front-matter --format json …")
```

Always pass `--format json` in agent loops; parse, don't scrape prose.

## Report back to the user

- output DOCX path
- profile used
- diagnostic counts (errors / warnings)
- any residual warnings you couldn't resolve
