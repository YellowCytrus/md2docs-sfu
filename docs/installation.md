# Установка (по агентам)

> Навигация: [Обзор синтаксиса](v2-overview.md) · [Рабочие процессы: веб](workflow-web.md) ·
> [Рабочие процессы: агент](workflow-agent.md)

Установка состоит из двух частей: **(1) сам конвертер** (нужен всегда, даже для веб-режима — чтобы
получить `.docx`) и **(2) интеграция с вашим ИИ-агентом** (опционально, для автоматического режима).

## Содержание

- [Шаг 1. Конвертер (нужен всем)](#шаг-1-конвертер-нужен-всем)
- [Шаг 2. Интеграция с агентом](#шаг-2-интеграция-с-агентом)
  - [Claude Code](#claude-code)
  - [Codex (OpenAI)](#codex-openai)
  - [OpenCode](#opencode)
  - [Gemini CLI](#gemini-cli)
  - [Antigravity](#antigravity)
  - [Веб-чат без агента](#веб-чат-без-агента)

## Шаг 1. Конвертер (нужен всем)

Рекомендуемый способ — изолированная установка через [pipx](https://pipx.pypa.io):

```bash
pipx install sfu-converter
sfu-converter --help      # проверка
```

Пока пакет не вышел на PyPI — ставьте прямо из репозитория (тоже одной строкой):

```bash
pipx install git+https://github.com/bounchich1/sfu_converter.git
```

Для разработки конвертера — см. [README → Разработка](../README.md#разработка)
(`pip install -e ".[dev]"`).

## Шаг 2. Интеграция с агентом

Выберите свой инструмент. Все варианты опираются на конвертер из шага 1.

Без `--only` команда `sfu-converter agents install` показывает найденные агенты. Автообнаружение
проверяет доступность команд в `PATH`: для Claude Code — `claude`, для Codex — `codex`. На Windows
установщик также умеет брать реальный путь Codex CLI из `CODEX_CLI_PATH` в `~/.codex/config.toml`,
если системный shim недоступен из оболочки. Если агент установлен, но не найден, запустите явный
вариант `--only <agent>` из той же оболочки, где доступны нужные команды.

### Claude Code

Самый богатый режим: набор скиллов (по одному на тип документа + общий `sfu-common`), которые
сами срабатывают по запросу.

```bash
sfu-converter agents install --only claude
```

Ручной вариант:

```text
/plugin marketplace add bounchich1/sfu_converter
/plugin install sfu-converter@sfu-converter
```

Повторный запуск безопасен: если marketplace или plugin уже добавлены, установщик продолжит
оставшиеся шаги.

После этого попросите: «сделай лабораторную №3 …» — нужный скилл активируется, покажет структуру
заголовков, спросит про содержание первых разделов, напишет `.txt`, прогонит lint и convert.

### Codex (OpenAI)

Установите Codex-плагин через встроенную команду конвертера:

```bash
sfu-converter agents install --only codex
```

Команда добавляет marketplace из репозитория и устанавливает `sfu-converter@sfu-converter` через
`codex plugin ...`. Для Codex плагин публикует один входной скилл `sfu-converter`, чтобы не нужно
было вручную вызывать общий и профильные скиллы по отдельности.

Ручной вариант:

```bash
codex plugin marketplace add bounchich1/sfu_converter
codex plugin add sfu-converter@sfu-converter
```

Ручной запасной вариант без плагина: Codex автоматически читает файл `AGENTS.md` в корне рабочего репозитория.
Скопируйте [`AGENTS.md`](../AGENTS.md) из этого проекта в корень вашего рабочего каталога (или
работайте прямо в клоне `sfu_converter`). Codex подхватит правила синтаксиса и цикл lint → convert.

```bash
cp /path/to/sfu_converter/AGENTS.md ./AGENTS.md
```

### OpenCode

OpenCode тоже читает `AGENTS.md` — действия те же, что для Codex. При желании можно описать
отдельного агента в `.opencode/` и сослаться на `AGENTS.md` как на инструкции.

### Gemini CLI

Gemini CLI читает `GEMINI.md`. Скопируйте [`GEMINI.md`](../GEMINI.md) (он генерируется из
`AGENTS.md` и содержит те же правила) в корень рабочего каталога.

```bash
cp /path/to/sfu_converter/GEMINI.md ./GEMINI.md
```

### Antigravity

Переносимого формата «скилла» нет. Подключите [`AGENTS.md`](../AGENTS.md) как файл правил/рабочего
процесса в настройках Antigravity, либо используйте веб-промпт (ниже). Поддержка по принципу
«best-effort»: инструмент новый, формат правил может меняться.

### Веб-чат без агента

Если у вас нет агента с доступом к терминалу — используйте Flow 1: один промпт
[`prompts/SFU_WEB_PROMPT.md`](../prompts/SFU_WEB_PROMPT.md). Подробности —
[workflow-web.md](workflow-web.md).
