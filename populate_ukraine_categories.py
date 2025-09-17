#!/usr/bin/env python3
"""
Скрипт для заполнения universal таблиц украинских категорий данными из таблиц источников
"""

import clickhouse_connect
from config import Config
import uuid
from datetime import datetime

def get_clickhouse_client():
    """Создает подключение к ClickHouse"""
    client_params = {
        'host': Config.CLICKHOUSE_HOST,
        'port': Config.CLICKHOUSE_PORT,
        'username': Config.CLICKHOUSE_USER,
        'database': Config.CLICKHOUSE_DATABASE
    }
    
    if Config.CLICKHOUSE_PASSWORD:
        client_params['password'] = Config.CLICKHOUSE_PASSWORD
    
    return clickhouse_connect.get_client(**client_params)

def populate_category_tables():
    """Заполняет universal таблицы данными из таблиц источников"""
    client = get_clickhouse_client()
    
    # Маппинг категорий к их источникам
    category_mappings = {
        'military_operations': [
            'news.lenta_military_operations',
            'news.gazeta_military_operations', 
            'news.kommersant_military_operations',
            'news.rbc_military_operations'
        ],
        'humanitarian_crisis': [
            'news.lenta_humanitarian_crisis',
            'news.gazeta_humanitarian_crisis',
            'news.kommersant_humanitarian_crisis',
            'news.rbc_humanitarian_crisis'
        ],
        'economic_consequences': [
            'news.lenta_economic_consequences',
            'news.gazeta_economic_consequences',
            'news.kommersant_economic_consequences', 
            'news.rbc_economic_consequences'
        ],
        'political_decisions': [
            'news.lenta_political_decisions',
            'news.gazeta_political_decisions',
            'news.kommersant_political_decisions',
            'news.rbc_political_decisions'
        ],
        'information_social': [
            'news.lenta_information_social',
            'news.gazeta_information_social',
            'news.kommersant_information_social',
            'news.rbc_information_social'
        ]
    }
    
    total_copied = 0
    
    for category, source_tables in category_mappings.items():
        target_table = f'news.universal_{category}'
        category_total = 0
        
        print(f"\n=== Обработка категории: {category} ===")
        
        for source_table in source_tables:
            try:
                # Проверяем, есть ли данные в источнике
                count_result = client.query(f'SELECT COUNT(*) FROM {source_table}')
                source_count = count_result.result_rows[0][0]
                
                if source_count == 0:
                    print(f"  {source_table}: пустая таблица, пропускаем")
                    continue
                
                # Копируем данные (только нужные колонки)
                insert_query = f"""
                INSERT INTO {target_table} (id, title, content, source, parsed_date, category)
                SELECT 
                    id,
                    title,
                    content,
                    source,
                    parsed_date,
                    category
                FROM {source_table}
                """
                
                client.command(insert_query)
                print(f"  {source_table}: скопировано {source_count} статей")
                category_total += source_count
                
            except Exception as e:
                print(f"  {source_table}: ошибка - {e}")
        
        print(f"Всего в категории {category}: {category_total} статей")
        total_copied += category_total
    
    print(f"\n=== ИТОГО СКОПИРОВАНО: {total_copied} статей ===")
    
    # Проверяем результат
    print("\n=== Проверка результатов ===")
    for category in category_mappings.keys():
        target_table = f'news.universal_{category}'
        try:
            result = client.query(f'SELECT COUNT(*) FROM {target_table}')
            count = result.result_rows[0][0]
            print(f"{target_table}: {count} статей")
        except Exception as e:
            print(f"{target_table}: ошибка - {e}")

if __name__ == "__main__":
    print("Начинаем заполнение universal таблиц украинских категорий...")
    populate_category_tables()
    print("Заполнение завершено!")