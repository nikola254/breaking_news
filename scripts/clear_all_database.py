#!/usr/bin/env python3
"""
Скрипт для полной очистки базы данных
Удаляет все таблицы и данные из ClickHouse
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config import Config

def clear_all_database():
    """Полная очистка базы данных"""
    print("🗑️ Начинаем полную очистку базы данных...")
    
    try:
        # Подключение к ClickHouse через HTTP
        base_url = f"http://{Config.CLICKHOUSE_HOST}:{Config.CLICKHOUSE_PORT}"
        auth = (Config.CLICKHOUSE_USER, Config.CLICKHOUSE_PASSWORD) if Config.CLICKHOUSE_USER else None
        
        print(f"✅ Подключение к ClickHouse: {Config.CLICKHOUSE_HOST}:{Config.CLICKHOUSE_PORT}")
        
        # Получаем список всех таблиц
        tables_query = f"SELECT name FROM system.tables WHERE database = '{Config.CLICKHOUSE_DATABASE}'"
        
        response = requests.get(
            f"{base_url}/",
            params={'query': tables_query},
            auth=auth,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Ошибка запроса: {response.status_code} - {response.text}")
            return False
        
        tables_text = response.text.strip()
        if not tables_text:
            print("ℹ️ База данных пуста - нет таблиц для удаления")
            return True
        
        tables = [line.strip() for line in tables_text.split('\n') if line.strip()]
        
        print(f"📋 Найдено таблиц: {len(tables)}")
        
        # Удаляем каждую таблицу
        deleted_tables = []
        for table_name in tables:
            try:
                # Удаляем таблицу
                drop_query = f"DROP TABLE IF EXISTS {Config.CLICKHOUSE_DATABASE}.{table_name}"
                
                response = requests.post(
                    f"{base_url}/",
                    data=drop_query,
                    auth=auth,
                    timeout=30
                )
                
                if response.status_code == 200:
                    deleted_tables.append(table_name)
                    print(f"✅ Удалена таблица: {table_name}")
                else:
                    print(f"❌ Ошибка при удалении таблицы {table_name}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ Ошибка при удалении таблицы {table_name}: {e}")
        
        print(f"\n🎯 Итоговая статистика:")
        print(f"   Удалено таблиц: {len(deleted_tables)}")
        print(f"   Удаленные таблицы: {', '.join(deleted_tables)}")
        
        # Проверяем, что база действительно пуста
        response = requests.get(
            f"{base_url}/",
            params={'query': tables_query},
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200 and not response.text.strip():
            print("✅ База данных полностью очищена!")
        else:
            remaining_tables = [line.strip() for line in response.text.split('\n') if line.strip()]
            print(f"⚠️ Остались таблицы: {remaining_tables}")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🗑️ ПОЛНАЯ ОЧИСТКА БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    success = clear_all_database()
    
    if success:
        print("\n🎉 База данных успешно очищена!")
        print("Теперь можно запускать парсеры для наполнения БД")
    else:
        print("\n❌ Ошибка при очистке базы данных")
