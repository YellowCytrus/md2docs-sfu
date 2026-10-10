import logging
from pathlib import Path

from sfu_converter.config import PathConfig
from sfu_converter.converter import TextToDocxConverter
from sfu_converter.menu import ConsoleMenu
from sfu_converter.validator import StyleValidator


def setup_logging(log_dir):
    """Настраивает логирование в файл и консоль"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / PathConfig.LOG_FILENAME

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    return logging.getLogger(__name__)


def main():
    """Точка входа в приложение"""
    base_dir = Path.cwd()

    logger = setup_logging(base_dir / PathConfig.LOGS_DIR)
    logger.info("Запуск приложения")

    converter = TextToDocxConverter(base_dir=base_dir)
    validator = StyleValidator()
    menu = ConsoleMenu(base_dir)

    try:
        menu.run(converter, validator)
    except KeyboardInterrupt:
        logger.info("Приложение завершено пользователем")
        print("\n\nПриложение завершено")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\n✗ Ошибка: {e}")


if __name__ == "__main__":
    main()
