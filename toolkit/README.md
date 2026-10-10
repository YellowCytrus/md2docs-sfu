# sfu-toolkit

Конвертер заметок Obsidian (Markdown) в документы Word по оформлению СФУ
(СТУ 7.5-07): титульник, настоящее поле Word «Содержание» с отточием, нумерация
таблиц и рисунков по разделам (1.1, 2.3, А.1 …), списки и таблицы как
Word-сущности, Times New Roman 14 pt, иллюстрации одинаковой ширины.

```
заметка.md (+ вложения)  →  заметка.txt (V2)  →  заметка.docx (+ .pdf)
```

## Состав репозитория

```
install.sh / install.ps1   установщики (Linux/macOS, Windows)
toolkit/config.example.json шаблон конфига
obsidian2sfu/              сама утилита + эталонный титульник + README
src/                       конвертер sfu_converter (с доработками оформления)
```

---

## Установка

Установщики **не ставят то, что уже есть**, и **спрашивают разрешение** перед
установкой отсутствующих системных пакетов (apt/dnf/pacman/zypper/brew — на Linux,
winget — на Windows).

### Linux / macOS

```bash
git clone https://github.com/bounchich1/sfu_converter.git
cd sfu_converter
./install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/bounchich1/sfu_converter.git
cd sfu_converter
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Нужен только Python 3.10+ (и Git для клонирования). Остальное установщик
предложит поставить. Неинтерактивно: `./install.sh` при `SFU_ASSUME_YES=1`
или `.\install.ps1 -Yes`.

Установщик создаёт `.venv`, ставит пакет (`pip install -e .`), кладёт команду
`obsidian2sfu` в PATH и создаёт конфиг.

---

## Запуск

```bash
# Linux
obsidian2sfu "Универ/Сети/Отчёт.md"

# Windows
obsidian2sfu "Универ\Сети\Отчёт.md"
```

Путь можно давать относительно хранилища (`--vault`, по умолчанию
`~/obsidian_backup`) или абсолютным. Рядом появятся `Отчёт.docx`, `Отчёт.txt`,
`images/` и PDF-превью (если установлен LibreOffice + poppler).

Флаги: `--out`, `--vault`, `--config ФАЙЛ`, `--set КЛЮЧ=ЗНАЧЕНИЕ`,
`--sources-file`, `--title-template`, `--no-pdf`.

---

## JSON-конфиги

Приоритет метаданных: значения по умолчанию → общий конфиг → конфиг заметки
→ `--config` → `--set`.

**Общий конфиг:**

- Linux/macOS: `~/.config/sfu/obsidian2sfu.json`
- Windows: `%APPDATA%\sfu\obsidian2sfu.json`

**Конфиг заметки** — файл рядом с `.md`, например `Отчёт.sfu.json`,
подхватывается автоматически.

```json
{
  "meta": {
    "document_type": "ОТЧЕТ О ПРАКТИЧЕСКОЙ РАБОТЕ №2",
    "title": "Задание 2",
    "student": "К. Д. Буданов",
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

Прочие ключи: `profile`, `sources`, `kv_first_cells`, `ref_fixes` — подробнее в
`obsidian2sfu/README.md`.

Разовое переопределение:

```bash
obsidian2sfu "Отчёт.md" --set title="Другая тема" --set year=2027
```

---

## Требования

| Компонент | Зачем | Обязателен |
|-----------|-------|------------|
| Python 3.10+ | конвертер | да |
| Git | клонирование | для установки |
| LibreOffice | PDF-превью | нет |
| poppler (`pdftotext`) | номера страниц в содержании | нет |

Без LibreOffice/poppler DOCX всё равно соберётся — номера страниц в содержании
пересчитает Word по Ctrl+A, F9.
