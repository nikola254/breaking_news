#!/usr/bin/env python3
"""
Скрипт для обновления схемы таблиц в ClickHouse
Добавляет новые поля для Gen-API классификатора
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config import Config

def update_table_schema():
    """Обновляет схему таблиц для включения новых полей"""
    print("🔄 Обновление схемы таблиц ClickHouse...")
    
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
            print("ℹ️ Нет таблиц для обновления")
            return True
        
        tables = [line.strip() for line in tables_text.split('\n') if line.strip()]
        print(f"📋 Найдено таблиц: {len(tables)}")
        
        # Поля для добавления
        new_fields = [
            "social_tension_index Float32 DEFAULT 0",
            "spike_index Float32 DEFAULT 0", 
            "ai_category String DEFAULT 'unknown'",
            "ai_confidence Float32 DEFAULT 0",
            "ai_classification_metadata String DEFAULT ''"
        ]
        
        updated_tables = []
        
        for table_name in tables:
            try:
                # Проверяем, есть ли уже эти поля
                check_query = f"DESCRIBE TABLE {Config.CLICKHOUSE_DATABASE}.{table_name}"
                
                response = requests.get(
                    f"{base_url}/",
                    params={'query': check_query},
                    auth=auth,
                    timeout=30
                )
                
                if response.status_code != 200:
                    print(f"⚠️ Не удалось проверить схему таблицы {table_name}")
                    continue
                
                existing_fields = response.text.lower()
                
                # Добавляем поля, которых нет
                fields_to_add = []
                for field in new_fields:
                    field_name = field.split()[0]
                    if field_name not in existing_fields:
                        fields_to_add.append(field)
                
                if fields_to_add:
                    # Добавляем поля
                    for field in fields_to_add:
                        alter_query = f"ALTER TABLE {Config.CLICKHOUSE_DATABASE}.{table_name} ADD COLUMN {field}"
                        
                        response = requests.post(
                            f"{base_url}/",
                            data=alter_query,
                            auth=auth,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            print(f"✅ Добавлено поле в {table_name}: {field.split()[0]}")
                        else:
                            print(f"❌ Ошибка добавления поля в {table_name}: {response.status_code}")
                    
                    updated_tables.append(table_name)
                else:
                    print(f"ℹ️ Таблица {table_name} уже содержит все необходимые поля")
                    
            except Exception as e:
                print(f"❌ Ошибка при обновлении таблицы {table_name}: {e}")
        
        print(f"\n🎯 Итоговая статистика:")
        print(f"   Обновлено таблиц: {len(updated_tables)}")
        print(f"   Обновленные таблицы: {', '.join(updated_tables[:10])}{'...' if len(updated_tables) > 10 else ''}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении схемы: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 ОБНОВЛЕНИЕ СХЕМЫ ТАБЛИЦ CLICKHOUSE")
    print("=" * 60)
    
    success = update_table_schema()
    
    if success:
        print("\n🎉 Схема таблиц успешно обновлена!")
        print("Теперь можно запускать парсеры с новыми полями")
    else:
        print("\n❌ Ошибка при обновлении схемы таблиц")
