#!/usr/bin/env python3
"""
Скрипт для миграции базы данных ClickHouse
Переименовывает столбец parsed_date в published_date во всех таблицах
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

def get_tables_with_parsed_date(client):
    """Получает список таблиц, содержащих столбец parsed_date"""
    try:
        # Получаем все таблицы из базы news
        query = """
        SELECT table, name as column_name
        FROM system.columns 
        WHERE database = 'news' AND name = 'parsed_date'
        ORDER BY table
        """
        result = client.query(query)
        tables = []
        for row in result.result_rows:
            tables.append(row[0])
        
        logger.info(f"Найдено {len(tables)} таблиц с столбцом parsed_date: {tables}")
        return tables
    except Exception as e:
        logger.error(f"Ошибка при получении списка таблиц: {e}")
        return []

def check_table_schema(client, table_name):
    """Проверяет схему конкретной таблицы"""
    try:
        query = f"""
        SELECT name, type 
        FROM system.columns 
        WHERE database = 'news' AND table = '{table_name}'
        ORDER BY position
        """
        result = client.query(query)
        logger.info(f"Схема таблицы {table_name}:")
        for row in result.result_rows:
            logger.info(f"  {row[0]}: {row[1]}")
        return result.result_rows
    except Exception as e:
        logger.error(f"Ошибка при проверке схемы таблицы {table_name}: {e}")
        return []

def rename_column_in_table(client, table_name):
    """Переименовывает столбец parsed_date в published_date в указанной таблице"""
    try:
        # В ClickHouse нельзя напрямую переименовать столбец
        # Нужно добавить новый столбец и скопировать данные
        
        # 1. Добавляем новый столбец published_date
        alter_query = f"""
        ALTER TABLE news.{table_name} 
        ADD COLUMN published_date DateTime DEFAULT now()
        """
        logger.info(f"Добавляем столбец published_date в таблицу {table_name}")
        client.command(alter_query)
        
        # 2. Копируем данные из parsed_date в published_date
        update_query = f"""
        ALTER TABLE news.{table_name} 
        UPDATE published_date = parsed_date 
        WHERE 1=1
        """
        logger.info(f"Копируем данные из parsed_date в published_date в таблице {table_name}")
        client.command(update_query)
        
        # 3. Удаляем старый столбец parsed_date
        drop_query = f"""
        ALTER TABLE news.{table_name} 
        DROP COLUMN parsed_date
        """
        logger.info(f"Удаляем столбец parsed_date из таблицы {table_name}")
        client.command(drop_query)
        
        logger.info(f"Миграция таблицы {table_name} завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при миграции таблицы {table_name}: {e}")
        return False

def main():
    """Основная функция миграции"""
    logger.info("Начинаем миграцию базы данных")
    
    # Подключаемся к ClickHouse
    client = get_clickhouse_client()
    if not client:
        logger.error("Не удалось подключиться к ClickHouse")
        return False
    
    try:
        # Получаем список таблиц с parsed_date
        tables = get_tables_with_parsed_date(client)
        if not tables:
            logger.info("Таблицы с столбцом parsed_date не найдены")
            return True
        
        # Проверяем схему каждой таблицы
        logger.info("Проверяем текущие схемы таблиц:")
        for table in tables:
            check_table_schema(client, table)
        
        # Выполняем миграцию для каждой таблицы
        success_count = 0
        for table in tables:
            logger.info(f"Начинаем миграцию таблицы {table}")
            if rename_column_in_table(client, table):
                success_count += 1
            else:
                logger.error(f"Миграция таблицы {table} не удалась")
        
        logger.info(f"Миграция завершена. Успешно обработано {success_count} из {len(tables)} таблиц")
        
        # Проверяем результат
        logger.info("Проверяем результат миграции:")
        remaining_tables = get_tables_with_parsed_date(client)
        if not remaining_tables:
            logger.info("Миграция прошла успешно! Столбцы parsed_date больше не найдены")
        else:
            logger.warning(f"Остались таблицы с parsed_date: {remaining_tables}")
        
        return success_count == len(tables)
        
    except Exception as e:
        logger.error(f"Общая ошибка миграции: {e}")
        return False
    
    finally:
        client.close()

if __name__ == "__main__":
    success = main()
    if success:
        print("Миграция базы данных завершена успешно!")
    else:
        print("Миграция базы данных завершилась с ошибками!")