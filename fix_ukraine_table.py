#!/usr/bin/env python3
"""
Скрипт для исправления таблицы ukraine_universal_news
Добавляет отсутствующий столбец 'source'
"""

import clickhouse_connect
import logging
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_clickhouse_client():
    """Создает подключение к ClickHouse"""
    try:
        client = clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            username=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        logger.info("Подключение к ClickHouse установлено")
        return client
    except Exception as e:
        logger.error(f"Ошибка подключения к ClickHouse: {e}")
        return None

def check_table_schema(client, table_name):
    """Проверяет схему таблицы"""
    try:
        query = f"""
        SELECT name, type 
        FROM system.columns 
        WHERE database = 'news' AND table = '{table_name}'
        ORDER BY position
        """
        result = client.query(query)
        logger.info(f"Схема таблицы {table_name}:")
        columns = []
        for row in result.result_rows:
            logger.info(f"  {row[0]}: {row[1]}")
            columns.append(row[0])
        return columns
    except Exception as e:
        logger.error(f"Ошибка при проверке схемы таблицы {table_name}: {e}")
        return []

def add_source_column(client, table_name):
    """Добавляет столбец source в таблицу"""
    try:
        # Проверяем, есть ли уже столбец source
        columns = check_table_schema(client, table_name)
        if 'source' in columns:
            logger.info(f"Столбец 'source' уже существует в таблице {table_name}")
            return True
        
        # Добавляем столбец source
        alter_query = f"""
        ALTER TABLE news.{table_name} 
        ADD COLUMN source String DEFAULT 'unknown'
        """
        logger.info(f"Добавляем столбец 'source' в таблицу {table_name}")
        client.command(alter_query)
        
        logger.info(f"Столбец 'source' успешно добавлен в таблицу {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении столбца 'source' в таблицу {table_name}: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("Начинаем исправление таблицы ukraine_universal_news")
    
    # Подключаемся к ClickHouse
    client = get_clickhouse_client()
    if not client:
        logger.error("Не удалось подключиться к ClickHouse")
        return False
    
    try:
        table_name = "ukraine_universal_news"
        
        # Проверяем текущую схему
        logger.info("Проверяем текущую схему таблицы:")
        check_table_schema(client, table_name)
        
        # Добавляем столбец source
        success = add_source_column(client, table_name)
        
        if success:
            # Проверяем результат
            logger.info("Проверяем результат:")
            check_table_schema(client, table_name)
            logger.info("Исправление таблицы завершено успешно!")
        else:
            logger.error("Исправление таблицы завершилось с ошибками!")
        
        return success
        
    except Exception as e:
        logger.error(f"Общая ошибка: {e}")
        return False
    
    finally:
        client.close()

if __name__ == "__main__":
    success = main()
    if success:
        print("Исправление таблицы ukraine_universal_news завершено успешно!")
    else:
        print("Исправление таблицы завершилось с ошибками!")