# SFU Converter — конвертер TXT в DOCX по стандарту СФУ

SFU Converter превращает структурированный текстовый файл (`.txt`) в документ
`.docx`, оформленный по стандарту Сибирского федерального университета
(СФУ, СТУ 7.5-07). Вы пишете содержимое простыми текстовыми маркерами, а
конвертер сам расставляет шрифты, поля, отступы, нумерацию, титульный лист,
подписи к рисункам и таблицам, список источников и формулы.

Что умеет конвертер:

- Несколько профилей оформления (лабораторные, курсовые, ВКР, отчёты по практике и др.).
- Автоматический титульный лист и нумерация страниц.
- Заголовки четырёх уровней, таблицы, рисунки, формулы, списки, сноски.
- Библиография по ГОСТ и перекрёстные ссылки между объектами.
- Проверка готового документа и диагностика ошибок в исходнике.

## ВАЖНО!
> Для сквозной генерации отчётов нужен
> DOCX-шаблон, в котором уже есть корректный титульный лист и содержание.
> В этом режиме конвертер не создаёт титульный лист и ToC автоматически, а
> добавляет только основное содержимое отчёта.

> Пока генерация титульников и ToC не готова до конца и может не соответсовать СТУ

> Используйте `--skip-generated-front-matter`


## Содержание

- [Краткий обзор](#sfu-converter--конвертер-txt-в-docx-по-стандарту-сфу)
- [Рабочие процессы](#рабочие-процессы)
  - [Flow 1 — веб-чат (ручной)](docs/workflow-web.md)
  - [Flow 2 — ИИ-агент (автоматический)](docs/workflow-agent.md)
- [Установка](#установка)
  - [Установка по агентам](docs/installation.md)
- [Быстрый старт](#быстрый-старт)
- [Команды CLI](#команды-cli)
- [Документация по стандарту и roadmap](#документация-по-стандарту-и-roadmap)
- [Профили оформления](#профили-оформления)
- [Разработка](#разработка)

## Рабочие процессы

Сгенерировать документ можно двумя способами:

- **Flow 1 — веб-чат (ручной).** Скопируйте один готовый промпт
  [`prompts/SFU_WEB_PROMPT.md`](prompts/SFU_WEB_PROMPT.md) в любой веб-чат с ИИ (Claude, ChatGPT,
  Gemini …). Он спросит тип документа и метаданные, выдаст `.txt` в синтаксисе V2, а вы
  сконвертируете его командами `sfu-converter`. Пошагово — [docs/workflow-web.md](docs/workflow-web.md).
- **Flow 2 — ИИ-агент (автоматический).** Агент (Claude Code, Codex, OpenCode, Gemini CLI) сам
  пишет `.txt`, прогоняет lint, исправляет ошибки и конвертирует в `.docx`. Пошагово —
  [docs/workflow-agent.md](docs/workflow-agent.md).

Оба способа спрашивают, **кто пишет первые разделы** (Цель/Задачи/Введение): вы даёте текст или ИИ
генерирует его из темы. Установка для каждого агента — [docs/installation.md](docs/installation.md).

## Установка

Рекомендуемый способ — изолированная установка через [pipx](https://pipx.pypa.io):

```bash
pipx install sfu-converter
# до выхода на PyPI — прямо из репозитория:
# pipx install git+https://github.com/bounchich1/sfu_converter
sfu-converter --help
```

Это всё, что нужно для конвертации `.txt → .docx`. Интеграция с ИИ-агентами (`sfu-converter agents
install` для Claude Code и Codex, `AGENTS.md`/`GEMINI.md` для остальных) и полная матрица установки по
инструментам — в [docs/installation.md](docs/installation.md). Установка для разработки конвертера — в
разделе [Разработка](#разработка).

## Быстрый старт

1. Создайте файл `report.txt` с разметкой версии 2:

   ```text
   [DOC syntax=2 profile=lab_practical_project_reports language=ru]
   [META key=title value="Отчёт по лабораторной работе"]
   [META key=student value="Иванов И. И."]
   [META key=group value="КИ22-01"]

   [H level=1 title="Введение"]
   [P] Цель работы — разработать REST API для каталога товаров.

   [H level=1 title="Заключение"]
   [P] Поставленные цели достигнуты.
   ```

2. Проверьте исходник на ошибки:

   ```bash
   sfu-converter lint --input report.txt --syntax-version 2
   ```

3. Сгенерируйте документ:

   ```bash
    sfu-converter convert --input report.txt --output report.docx --profile lab_practical_project_reports --syntax-version 2 --template template1.docx --skip-generated-front-matter
   ```

## Команды CLI

```bash
sfu-converter <команда> [параметры]
```

| Команда           | Назначение                                  |
|-------------------|---------------------------------------------|
| `convert`         | Преобразовать TXT в DOCX (или PPTX)         |
| `validate-docx`   | Проверить готовый DOCX по профилю           |
| `parse`           | Разобрать TXT в AST (JSON)                  |
| `lint`            | Проверить синтаксис TXT и правила профиля   |
| `list-profiles`   | Показать доступные профили оформления       |
| `explain-syntax`  | Вывести справку по синтаксису               |
| `export-schema`   | Экспортировать JSON-схемы                    |
| `export-coverage` | Вывести матрицу покрытия стандарта          |
| `agents`          | Установить скиллы в AI-агенты (Claude, Codex)|

Частые флаги: `--syntax-version 2`, `--profile <имя>`, `--strict`
(предупреждения как ошибки), `--output-format pptx`,
`--template <путь>` (шаблон титульного листа),
`--skip-generated-front-matter` (не создавать титульный лист и содержание).


## Документация по стандарту и roadmap

Полное описание синтаксиса версии 2 разбито на тематические страницы в папке
[`docs/`](docs/):

Сводные материалы по стандарту и развитию проекта: `docs/sfu-standard-coverage-matrix.md`
и `docs/technical requirements/08_migration_roadmap.md`.

- [Обзор и структура документа](docs/v2-overview.md) — `[DOC]`, `[META]`,
  правила атрибутов, общий каркас файла.
- [Текст и заголовки](docs/v2-text.md) — `[H]`, `[STRUCTURAL]`, `[P]`,
  выделение текста, `[RAW]`.
- [Объекты: рисунки, таблицы, списки, формулы](docs/v2-objects.md) —
  `[FIGURE]`, `[TABLE]`, `[LIST]`, `[FORMULA]`.
- [Ссылки, сноски и источники](docs/v2-references.md) — `[REF]`, `[FN]`,
  `[SOURCE]`, библиография по ГОСТ.
- [Расширенные блоки](docs/v2-extensions.md) — `[SECTION]`, `[APPENDIX]`,
  `[ABBREVIATIONS]`, `[DESIGNATION]`, графические материалы и слайды.
- [Диагностика и проверки](docs/v2-diagnostics.md) — коды ошибок, строгий
  режим, предупреждение о кириллице в маркерах.
- [Профили оформления](docs/v2-profiles.md) — список профилей и их выбор.

Готовый демонстрационный файл со всеми возможностями:
[`examples/converter_v2_showcase_report.txt`](examples/converter_v2_showcase_report.txt).

## Профили оформления

```bash
sfu-converter list-profiles --format json
```

| Профиль                               | Назначение                                |
|---------------------------------------|-------------------------------------------|
| `common`                              | Общие базовые правила                      |
| `lab_practical_project_reports`       | Лабораторные, практические, проектные      |
| `practice_reports`                    | Отчёты по практике                         |
| `research_reports`                    | Отчёты о НИР                               |
| `coursework`                          | Курсовые проекты и работы                  |
| `graduation_qualification_work`       | ВКР (выпускная квалификационная работа)    |
| `small_written_works`                 | Рефераты, контрольные, РГЗ, эссе           |
| `graphic_and_demonstration_materials` | Графические и демонстрационные материалы   |
| `project_designations`                | Обозначения проектов                       |

Подробнее — в [docs/v2-profiles.md](docs/v2-profiles.md).

## Разработка

```bash
git clone https://github.com/bounchich1/sfu_converter
cd sfu_converter
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"

python -m pytest                                                              # тесты
python -m pytest --cov=sfu_converter --cov-branch --cov-report=term-missing   # покрытие
```

В режиме разработки команда доступна и как `sfu-converter`, и как `python -m sfu_converter.cli`.
Портативные инструкции для агентов: `AGENTS.md` — источник правды, `GEMINI.md` генерируется из него
командой `python tools/sync_agent_docs.py` (проверка в CI — `--check`).

Структура проекта:

```
src/sfu_converter/
  cli.py              # точка входа CLI
  parser/             # парсер TXT версии 2
  domain/             # узлы AST, правила оформления, диагностика
  application/        # сценарии композиции и конвертации
  infrastructure/     # рендерер DOCX, валидатор, титульные листы
  registry/           # реестр профилей и правил
  tools/              # проверка кириллицы в маркерах
docs/                 # вики и требования к оформлению
examples/             # примеры TXT-файлов
templates/            # шаблоны DOCX
```
