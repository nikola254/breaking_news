# Скрипт для миграции существующих данных в категоризированные таблицы

from news_categories import migrate_existing_data
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Запуск миграции существующих данных в категоризированные таблицы...")
    try:
        migrate_existing_data()
        logger.info("Миграция данных успешно завершена!")
    except Exception as e:
        logger.error(f"Ошибка при миграции данных: {e}")