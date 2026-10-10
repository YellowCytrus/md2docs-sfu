#!/usr/bin/env python3
"""Анализатор и исправитель кириллических символов в маркерах TXT файлов"""

import re
import shutil
from pathlib import Path

from sfu_converter.config import PathConfig

CYRILLIC_TO_LATIN = {
    "А": "A",
    "В": "B",
    "Е": "E",
    "К": "K",
    "М": "M",
    "Н": "H",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Т": "T",
    "Х": "X",
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
}


def find_markers(line):
    """Находит все маркеры в строке и возвращает позиции"""
    markers = []
    for match in re.finditer(r"\[([^\]]+)\]", line):
        markers.append({"start": match.start(), "end": match.end(), "content": match.group(1), "full": match.group(0)})
    return markers


def fix_marker_content(content):
    """Заменяет кириллические символы на латинские в содержимом маркера"""
    fixed = []
    changes = []
    for char in content:
        if char in CYRILLIC_TO_LATIN:
            fixed.append(CYRILLIC_TO_LATIN[char])
            changes.append(char)
        else:
            fixed.append(char)
    return "".join(fixed), changes


def fix_file(file_path, create_backup=True):
    """Исправляет кириллицу в маркерах файла. Возвращает статистику"""
    stats = {"fixed": 0, "failed": 0, "changes": []}

    # Создаём резервную копию
    if create_backup:
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
        shutil.copy2(file_path, backup_path)
        print(f"  Backup: {backup_path.name}")

    # Читаем файл
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    fixed_lines = []

    for line_num, line in enumerate(lines, 1):
        markers = find_markers(line)

        if not markers:
            fixed_lines.append(line)
            continue

        # Обрабатываем каждый маркер в строке
        new_line = line
        offset = 0

        for marker in markers:
            fixed_content, changes = fix_marker_content(marker["content"])

            if changes:
                # Заменяем маркер
                new_marker = f"[{fixed_content}]"
                start = marker["start"] + offset
                end = marker["end"] + offset

                new_line = new_line[:start] + new_marker + new_line[end:]
                offset += len(new_marker) - len(marker["full"])

                stats["fixed"] += len(changes)
                stats["changes"].append({"line": line_num, "old": marker["full"], "new": new_marker, "chars": changes})

        fixed_lines.append(new_line)

    # Записываем исправленный файл
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)

    return stats


def verify_file(file_path):
    """Проверяет файл после исправления на оставшиеся ошибки"""
    remaining = []

    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            markers = find_markers(line)
            for marker in markers:
                for char in marker["content"]:
                    if char in CYRILLIC_TO_LATIN:
                        remaining.append({"line": line_num, "marker": marker["full"], "char": char})
                        break

    return remaining


def main():
    """Запуск анализатора и исправителя"""
    print("=" * 70)
    print("ИСПРАВИТЕЛЬ КИРИЛЛИЧЕСКИХ СИМВОЛОВ В МАРКЕРАХ")
    print("=" * 70)

    # Директория с примерами
    examples_dir = Path.cwd() / PathConfig.EXAMPLES_DIR

    if not examples_dir.exists():
        print(f"\nWARNING: Директория не найдена: {examples_dir}")
        return

    # Поиск всех TXT файлов (исключаем бэкапы)
    txt_files = sorted([f for f in examples_dir.glob("*.txt") if not f.name.endswith(".backup")])

    if not txt_files:
        print(f"\nWARNING: TXT файлы не найдены в {examples_dir}")
        return

    print(f"\nДиректория: {examples_dir}")
    print(f"Найдено файлов: {len(txt_files)}")
    print()

    total_fixed = 0
    total_remaining = 0
    files_processed = 0

    # === ЭТАП 1: Исправление ===
    print("=" * 70)
    print("ЭТАП 1: ИСПРАВЛЕНИЕ ФАЙЛОВ")
    print("=" * 70)
    print()

    for txt_file in txt_files:
        stats = fix_file(txt_file, create_backup=True)

        if stats["fixed"] > 0:
            files_processed += 1
            total_fixed += stats["fixed"]

            print(f"EDIT: {txt_file.name}")
            print(f"    Исправлено замен: {stats['fixed']}")

            for change in stats["changes"][:5]:  # Показываем первые 5
                chars_str = ", ".join(f"'{c}'->'{CYRILLIC_TO_LATIN[c]}'" for c in change["chars"])
                print(f"    Строка {change['line']}: {change['old']} -> {change['new']}")
                print(f"           {chars_str}")

            if len(stats["changes"]) > 5:
                print(f"    ... и ещё {len(stats['changes']) - 5} замен")
            print()
        else:
            print(f"OK: {txt_file.name} - ошибок не найдено")

    # === ЭТАП 2: Проверка ===
    print()
    print("=" * 70)
    print("ЭТАП 2: ПРОВЕРКА ПОСЛЕ ИСПРАВЛЕНИЯ")
    print("=" * 70)
    print()

    for txt_file in txt_files:
        remaining = verify_file(txt_file)

        if remaining:
            total_remaining += len(remaining)
            print(f"WARNING: {txt_file.name} - осталось проблем: {len(remaining)}")

            for issue in remaining[:3]:  # Показываем первые 3
                print(f"    Строка {issue['line']}: {issue['marker']} (символ '{issue['char']}')")

            if len(remaining) > 3:
                print(f"    ... и ещё {len(remaining) - 3}")
            print()
        else:
            print(f"OK: {txt_file.name} - чисто")

    # === ИТОГОВЫЙ ОТЧЁТ ===
    print()
    print("=" * 70)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 70)
    print(f"  Обработано файлов:    {files_processed} из {len(txt_files)}")
    print(f"  Исправлено ошибок:    {total_fixed}")
    print(f"  Осталось проблем:     {total_remaining}")
    print()

    if total_remaining == 0:
        print("OK: Все файлы исправлены успешно!")
        print("   Теперь можно запускать конвертацию.")
    else:
        print("WARNING: Некоторые ошибки не удалось исправить автоматически.")
        print("   Проверьте файлы вручную.")

    print()
    print("Бэкапы сохранены с расширением .txt.backup")
    print("   Для отката: скопируйте .backup поверх .txt")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
