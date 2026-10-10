import sys
from pathlib import Path

from sfu_converter.config import PathConfig
from sfu_converter.domain.constants import DEFAULT_PROFILE_NAME
from sfu_converter.registry import get_profile


class ConsoleMenu:
    """Консольное меню приложения"""

    def __init__(self, base_dir):
        """Инициализация меню"""
        self.base_dir = Path(base_dir)
        self.selected_template = None
        self.selected_files = []

    def clear_screen(self):
        """Очищает экран консоли"""
        print("\033[2J\033[H", end="", flush=True)

    def print_header(self, title):
        """Выводит заголовок меню"""
        self.clear_screen()
        print("=" * 60)
        print(f" {title}")
        print("=" * 60)
        print()

    def get_txt_files(self):
        """Получает список TXT файлов из директории examples"""
        examples_dir = self.base_dir / PathConfig.EXAMPLES_DIR
        if not examples_dir.exists():
            return []
        return sorted([f.name for f in examples_dir.iterdir() if f.suffix == ".txt"])

    def get_templates(self):
        """Получает список шаблонов из директории templates"""
        templates_dir = self.base_dir / PathConfig.TEMPLATES_DIR
        if not templates_dir.exists():
            return []
        return sorted([f.name for f in templates_dir.iterdir() if f.suffix == ".docx"])

    def output_name_for(self, txt_file):
        return Path(txt_file).with_suffix(".docx").name

    def select_template(self):
        """Меню выбора шаблона"""
        templates = self.get_templates()

        if not templates:
            print("⚠️  Шаблоны не найдены в директории templates/")
            print("   Создайте файл .docx в папке templates/ или нажмите Enter для работы без шаблона")
            input("\nНажмите Enter для продолжения...")
            return None

        print("\nДоступные шаблоны:")
        print("0. Без шаблона (создать новый документ)")
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template}")

        choice = input(f"\nВыберите шаблон (0-{len(templates)}): ")

        if choice.isdigit():
            idx = int(choice)
            if idx == 0:
                self.selected_template = None
                print("✓ Выбрано: без шаблона")
            elif 1 <= idx <= len(templates):
                self.selected_template = templates[idx - 1]
                print(f"✓ Выбран шаблон: {self.selected_template}")
            else:
                print("✗ Неверный выбор")

        input("\nНажмите Enter для продолжения...")
        return self.selected_template

    def select_files(self):
        """Меню выбора файлов для конвертации"""
        txt_files = self.get_txt_files()

        if not txt_files:
            print("\n⚠️  TXT файлы не найдены в директории examples/")
            input("\nНажмите Enter для продолжения...")
            return []

        print("\nДоступные файлы:")
        for i, file in enumerate(txt_files, 1):
            print(f"{i}. {file}")
        print(f"A. Выбрать все ({len(txt_files)} файлов)")
        print("0. Назад")

        choice = input("\nВыберите файлы (номера через запятую, или 'a'): ").strip().lower()

        if choice == "a":
            self.selected_files = txt_files
            print(f"✓ Выбрано файлов: {len(self.selected_files)}")
        elif choice == "0":
            return []
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
                self.selected_files = [txt_files[i] for i in indices if 0 <= i < len(txt_files)]
                print(f"✓ Выбрано файлов: {len(self.selected_files)}")
            except (ValueError, IndexError):
                print("✗ Неверный выбор")
                return []

        input("\nНажмите Enter для продолжения...")
        return self.selected_files

    def show_main_menu(self):
        """Показывает главное меню"""
        self.print_header("КОНВЕРТЕР TXT В DOCX (Стандарт СФУ)")
        print("1. Выбрать шаблон" + (f" [{self.selected_template}]" if self.selected_template else ""))
        print(
            "2. Выбрать файлы для конвертации"
            + (f" [{len(self.selected_files)} файлов]" if self.selected_files else "")
        )
        print("3. Начать конвертацию")
        print("4. Валидировать последний результат")
        print("0. Выход")
        print()

        return input("Выберите действие (0-4): ").strip()

    def run(self, converter, validator):
        """Запускает главное меню приложения"""
        while True:
            choice = self.show_main_menu()

            if choice == "1":
                self.select_template()

            elif choice == "2":
                self.select_files()

            elif choice == "3":
                if not self.selected_files:
                    print("\n⚠️  Сначала выберите файлы для конвертации!")
                    input("\nНажмите Enter для продолжения...")
                    continue

                print(f"\n{'=' * 60}")
                print(" НАЧАЛО КОНВЕРТАЦИИ")
                print(f"{'=' * 60}")
                print(f"Шаблон: {self.selected_template or 'Нет (новый документ)'}")
                print(f"Файлов: {len(self.selected_files)}")
                print()

                for txt_file in self.selected_files:
                    output_name = self.output_name_for(txt_file)
                    print(f"→ Конвертация: {txt_file} → {output_name}")

                    try:
                        input_file = self.base_dir / PathConfig.EXAMPLES_DIR / txt_file
                        output_file = self.base_dir / PathConfig.RESULTS_DIR / output_name
                        converter.convert_file(
                            input_file,
                            output_file,
                            self.selected_template,
                            profile=get_profile(DEFAULT_PROFILE_NAME),
                        )
                        print("  ✓ Успешно")
                    except Exception as e:
                        print(f"  ✗ Ошибка: {e}")

                print(f"\n{'=' * 60}")
                print("✓ Конвертация завершена!")
                print(f"{'=' * 60}")
                input("\nНажмите Enter для продолжения...")

            elif choice == "4":
                print("\nВалидация последнего результата...")
                results_dir = self.base_dir / PathConfig.RESULTS_DIR
                docx_files = (
                    sorted([f for f in results_dir.iterdir() if f.suffix == ".docx"]) if results_dir.exists() else []
                )

                if docx_files:
                    last_file = docx_files[-1]
                    print(f"Проверка: {last_file.name}")
                    is_valid = validator.validate_file(str(last_file))
                    if is_valid:
                        print("✅ Документ соответствует стандарту СФУ")
                    else:
                        report = validator.get_report()
                        print(f"⚠️  Найдено ошибок: {report['errors']}")
                else:
                    print("⚠️  Нет сгенерированных файлов")

                input("\nНажмите Enter для продолжения...")

            elif choice == "0":
                print("\nДо свидания!")
                sys.exit(0)

            else:
                print("\n✗ Неверный выбор")
                input("\nНажмите Enter для продолжения...")
