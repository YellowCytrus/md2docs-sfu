# Metadata (`[META]`) per profile

Each profile requires a minimum set of `[META]` fields for the title page. A missing required
field raises `TXT_MISSING_METADATA`. Never invent ФИО, group, supervisor, or dates — ask the user.

## Always gather first (every profile)

| key         | meaning                       |
|-------------|-------------------------------|
| `title`     | тема / название работы        |
| `student`   | ФИО студента (`Иванов И. И.`) |
| `group`     | учебная группа (`КИ22-01`)    |
| `year`      | год                           |

Strongly recommended: `supervisor` (руководитель), `city` (обычно `Красноярск`),
`discipline` (дисциплина), `university`, `institute`, `department`.

## Common keys recognized

`title`, `student`, `group`, `supervisor`, `teacher`, `city`, `year`, `university`, `institute`,
`department`, `discipline`, `document_type`.

## Required `[META]` per profile (authoritative — from the rule registry)

| Profile                          | **Required** keys                                  | Useful optional keys |
|----------------------------------|----------------------------------------------------|----------------------|
| `lab_practical_project_reports`  | `document_type`, `title`, `student`, `group`, `teacher` | `discipline`, `institute`, `department`, `city`, `year` |
| `practice_reports`               | `title`, `student`, `group`                        | `document_type`, `supervisor`, `institute`, `department`, `city`, `year` |
| `research_reports`               | `title`, `student`, `group`                        | `document_type`, `supervisor`, `department`, `city`, `year` |
| `coursework`                     | `title`, `student`, `group`, `supervisor`          | `document_type`, `discipline`, `department`, `city`, `year` |
| `graduation_qualification_work`  | `title`, `student`, `supervisor`                   | `department`, `institute`, `reviewer`, `consultants`, `norm_controller`, `city`, `year` |
| `small_written_works`            | `title`, `student`, `group`                        | `document_type`, `discipline`, `city`, `year` |

Notes:
- **`teacher`** (преподаватель) is required for lab reports; **`supervisor`** (руководитель) for
  coursework / ВКР. They are different keys — use the one the profile asks for.
- `document_type` is the human title of the work (e.g. «Отчёт по лабораторной работе»); each
  profile also has a sensible default, but lab reports require it explicitly.
- Keep `[TITLE_PAGE]` after the `[META]` block, but note it's **skipped by default**: built-in
  title-page generation is in active development and may not match СТУ, so the default convert ships
  the title page (and ToC) from a DOCX template via `--template … --skip-generated-front-matter`
  (see `cli.md`). `[TITLE_PAGE]` stays as the re-enable point for when generation is ready; without
  the skip flag it would otherwise produce the advisory `STRUCTURE_TITLE_PAGE_MISSING` warning.

> If unsure, run `sfu-converter lint --profile <P> … --format json` and add whatever
> `TXT_MISSING_METADATA` reports.
