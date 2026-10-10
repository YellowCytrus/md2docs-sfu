# md2docs-sfu

Конвертер заметок **Obsidian (Markdown) → документы Word по оформлению СФУ**
(СТУ 7.5-07). Из markdown-заметки с вложениями собирается `.txt` в синтаксисе V2
и затем `.docx`:

```
заметка.md (+ вложения)  →  заметка.txt (V2)  →  заметка.docx (+ .pdf)
```

Что получается в документе:

- титульный лист из шаблона с подстановкой ваших данных (ФИО, группа, кафедра, тема, преподаватель);
- настоящее поле Word «Содержание» с отточием;
- нумерация **таблиц и рисунков по разделам** — `1.1`, `2.3`, в приложениях `А.1`, `Б.2`
  (структурные разделы — ВВЕДЕНИЕ, СОДЕРЖАНИЕ, СПИСОК ИСТОЧНИКОВ — не учитываются);
- списки и таблицы как Word-сущности, Times New Roman 14 pt, поля по СТУ;
- иллюстрации одинаковой ширины, симметрично полям, с отбивкой по строке сверху/снизу;
- список источников перед приложениями.

---

## Установка

Нужен только **Python 3.10+** (и Git для клонирования). Установщик сам проверяет,
что уже стоит, и **спрашивает разрешение** перед установкой отсутствующих системных
пакетов (apt/dnf/pacman/zypper/brew — Linux, winget — Windows).

### Linux / macOS

```bash
git clone https://github.com/YellowCytrus/md2docs-sfu.git
cd md2docs-sfu
./install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/YellowCytrus/md2docs-sfu.git
cd md2docs-sfu
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Неинтерактивно: `SFU_ASSUME_YES=1 ./install.sh` или `.\install.ps1 -Yes`.

Установщик создаёт `.venv`, ставит пакет (`pip install -e .`), кладёт команду
`obsidian2sfu` в PATH и создаёт конфиг.

---

## Запуск

```bash
# Linux / macOS
obsidian2sfu "Универ/Сети/Отчёт.md"

# Windows
obsidian2sfu "Универ\Сети\Отчёт.md"
```

Путь можно давать относительно хранилища (`--vault`, по умолчанию
`~/obsidian_backup`) или абсолютным. Рядом появятся `Отчёт.docx`, `Отчёт.txt`,
папка `images/` и PDF-превью (если установлен LibreOffice + poppler).

Флаги: `--out`, `--vault`, `--config ФАЙЛ`, `--set КЛЮЧ=ЗНАЧЕНИЕ`,
`--sources-file`, `--title-template`, `--no-pdf`.

---

## JSON-конфиги

Метаданные титульника берутся по приоритету: значения по умолчанию → общий конфиг
→ конфиг заметки → `--config` → `--set`.

**Общий конфиг:**

- Linux/macOS: `~/.config/sfu/obsidian2sfu.json`
- Windows: `%APPDATA%\sfu\obsidian2sfu.json`

**Конфиг заметки** — файл рядом с `.md` (например, `Отчёт.sfu.json`),
подхватывается автоматически.

```json
{
  "meta": {
    "document_type": "ОТЧЕТ О ПРАКТИЧЕСКОЙ РАБОТЕ №2",
    "title": "Задание 2",
    "student": "Иванов И. И.",
    "group": "КИ23-14Б",
    "record_book": "032319377",
    "teacher": "Д. В. Зябликов",
    "institute": "Институт космических и информационных технологий",
    "department": "Информационные системы и технологии",
    "city": "Красноярск",
    "year": "2026"
  },
  "sources": ["Источник 1", "Источник 2"]
}
```

| Ключ `meta` | На титульнике |
|-------------|----------------|
| `document_type` | вид работы |
| `title` | тема (в кавычках) |
| `student`, `group`, `record_book` | студент, группа, зачётка |
| `teacher` | преподаватель |
| `institute`, `department` | институт, кафедра |
| `city`, `year` | город, год |

Разовое переопределение:

```bash
obsidian2sfu "Отчёт.md" --set title="Другая тема" --set year=2027
```

---

## Структура

```
install.sh / install.ps1     установщики (Linux/macOS, Windows)
toolkit/                     инструкция и шаблон конфига
obsidian2sfu/                утилита + эталонный титульник + README
src/                         конвертер sfu_converter (с доработками оформления)
```

## Требования

| Компонент | Зачем | Обязателен |
|-----------|-------|------------|
| Python 3.10+ | конвертер | да |
| Git | клонирование | для установки |
| LibreOffice | PDF-превью | нет |
| poppler (`pdftotext`) | номера страниц в содержании | нет |

Без LibreOffice/poppler DOCX всё равно собирается — номера страниц в содержании
пересчитает Word по `Ctrl+A, F9`.

Подробности — в [toolkit/README.md](toolkit/README.md) и
[obsidian2sfu/README.md](obsidian2sfu/README.md).
