#!/usr/bin/env python3
"""
Скрипт для проверки структуры таблицы universal_military_operations
"""

from clickhouse_driver import Client
from config import Config

def check_table_structure():
    """Проверяет структуру таблицы universal_military_operations"""
    try:
        # Подключение к ClickHouse
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=Config.CLICKHOUSE_DATABASE
        )
        
        # Получаем структуру таблицы
        result = client.execute("DESCRIBE TABLE news.universal_military_operations")
        
        print("=== Структура таблицы universal_military_operations ===")
        for row in result:
            print(f"{row[0]}: {row[1]}")
            
        # Получаем несколько записей для примера
        print("\n=== Пример записей ===")
        result = client.execute("SELECT * FROM news.universal_military_operations LIMIT 3")
        
        for row in result:
            print(f"ID: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Link: {row[2]}")
            print(f"Content: {row[3][:100]}...")
            print(f"Source: {row[4]}")
            print(f"Category: {row[5]}")
            print("---")
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")

if __name__ == "__main__":
    check_table_structure()