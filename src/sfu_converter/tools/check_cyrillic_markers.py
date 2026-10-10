#!/usr/bin/env python3
"""Анализатор кириллических символов в маркерах TXT файлов"""

import re
from pathlib import Path

from sfu_converter.config import PathConfig

CYRILLIC_LETTERS = {
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


def check_file(file_path):
    """Проверяет файл на кириллицу в маркерах"""
    issues = []

    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Ищем все маркеры в квадратных скобках
            matches = re.findall(r"\[([^\]]+)\]", line)
            for marker in matches:
                # Проверяем каждый символ маркера
                for char in marker:
                    if char in CYRILLIC_LETTERS:
                        issues.append(
                            {
                                "line": line_num,
                                "marker": marker,
                                "char": char,
                                "suggestion": CYRILLIC_LETTERS[char],
                                "text": line.strip()[:60],
                            }
                        )
                        break  # Одна ошибка на маркер

    return issues


def main():
    """Запуск анализатора"""
    print("=" * 70)
    print("АНАЛИЗАТОР КИРИЛЛИЧЕСКИХ СИМВОЛОВ В МАРКЕРАХ")
    print("=" * 70)

    # Директория с примерами
    examples_dir = Path.cwd() / PathConfig.EXAMPLES_DIR

    if not examples_dir.exists():
        print(f"\nWARNING: Директория не найдена: {examples_dir}")
        print("   Создайте папку examples/ и поместите туда TXT файлы")
        return

    # Поиск всех TXT файлов
    txt_files = sorted(examples_dir.glob("*.txt"))

    if not txt_files:
        print(f"\nWARNING: TXT файлы не найдены в {examples_dir}")
        return

    print(f"\nДиректория: {examples_dir}")
    print(f"Найдено файлов: {len(txt_files)}")
    print()

    total_issues = 0
    files_with_issues = 0

    for txt_file in txt_files:
        issues = check_file(txt_file)

        if issues:
            files_with_issues += 1
            total_issues += len(issues)

            print(f"\n{'-' * 70}")
            print(f"ERROR: {txt_file.name} - найдено проблем: {len(issues)}")
            print(f"{'-' * 70}")

            for issue in issues:
                print(f"  Строка {issue['line']}: [{issue['marker']}]")
                print(f"    WARNING: Кириллическая '{issue['char']}' -> замените на '{issue['suggestion']}'")
                print(f"    Текст: {issue['text']}...")
                print()
        else:
            print(f"OK: {txt_file.name} - ошибок нет")

    # Итоговый отчёт
    print(f"\n{'=' * 70}")
    print("ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'=' * 70}")
    print(f"  Проверено файлов:     {len(txt_files)}")
    print(f"  Файлов с ошибками:    {files_with_issues}")
    print(f"  Всего проблем:        {total_issues}")

    if total_issues == 0:
        print("\nOK: Все файлы корректны! Маркеры используют латинские символы.")
    else:
        print("\nWARNING: Найдены проблемы! Замените кириллические символы в маркерах.")
        print("   Пример: [Н1] -> [H1], [ТABLE_START] -> [TABLE_START]")

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
