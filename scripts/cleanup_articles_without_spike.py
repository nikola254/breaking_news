#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для очистки базы данных от статей без spike_index
"""

import sys
import os
from clickhouse_driver import Client

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def cleanup_articles_without_spike():
    """Удаляет статьи без spike_index из всех таблиц"""
    
    print("\n" + "=" * 60)
    print("🧹 ОЧИСТКА БАЗЫ ДАННЫХ ОТ СТАТЕЙ БЕЗ SPIKE_INDEX")
    print("=" * 60)
    
    # Подключение к ClickHouse
    try:
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=Config.CLICKHOUSE_DATABASE
        )
        print("✅ Подключение к ClickHouse успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения к ClickHouse: {e}")
        return
    
    try:
        # Получаем список всех таблиц в базе news
        tables_query = """
        SELECT name 
        FROM system.tables 
        WHERE database = 'news'
        ORDER BY name
        """
        
        tables_result = client.execute(tables_query)
        tables = [row[0] for row in tables_result]
        
        print(f"\n📋 Найдено таблиц: {len(tables)}")
        
        total_deleted = 0
        processed_tables = 0
        
        for table_name in tables:
            try:
                # Проверяем наличие колонки spike_index
                columns_query = f"""
                SELECT name 
                FROM system.columns 
                WHERE database = 'news' 
                AND table = '{table_name}' 
                AND name = 'spike_index'
                """
                
                columns_result = client.execute(columns_query)
                
                if not columns_result:
                    print(f"⏭️  Таблица {table_name} не содержит колонку spike_index - пропускаем")
                    continue
                
                # Подсчитываем количество записей без spike_index
                count_query = f"""
                SELECT COUNT(*) 
                FROM news.{table_name} 
                WHERE spike_index = 0 OR spike_index IS NULL
                """
                
                count_result = client.execute(count_query)
                count_to_delete = count_result[0][0]
                
                if count_to_delete == 0:
                    print(f"✅ Таблица {table_name}: нет записей для удаления")
                    continue
                
                # Удаляем записи без spike_index
                delete_query = f"""
                DELETE FROM news.{table_name} 
                WHERE spike_index = 0 OR spike_index IS NULL
                """
                
                print(f"🗑️  Удаляем {count_to_delete} записей из таблицы {table_name}...")
                client.execute(delete_query)
                
                total_deleted += count_to_delete
                processed_tables += 1
                
                print(f"✅ Таблица {table_name}: удалено {count_to_delete} записей")
                
            except Exception as e:
                print(f"⚠️  Ошибка при обработке таблицы {table_name}: {e}")
                continue
        
        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 60)
        print(f"Обработано таблиц: {processed_tables}")
        print(f"Всего удалено записей: {total_deleted}")
        print("=" * 60)
        
        if total_deleted > 0:
            print("\n🎉 Очистка завершена успешно!")
            print("Теперь все статьи в базе данных имеют корректные индексы spike_index")
        else:
            print("\n✨ Очистка не требовалась - все статьи уже имеют spike_index")
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении очистки: {e}")
    
    finally:
        pass  # ClickHouse client не требует явного закрытия

if __name__ == "__main__":
    cleanup_articles_without_spike()
