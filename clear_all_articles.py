#!/usr/bin/env python3
"""
Скрипт для удаления всех статей из базы данных.
Очищает все таблицы новостей и сбрасывает счетчики.
"""

import clickhouse_connect
from config import Config
import sys

def get_clickhouse_client():
    """Создание клиента ClickHouse."""
    if Config.CLICKHOUSE_PASSWORD:
        return clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            username=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
    else:
        return clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            username=Config.CLICKHOUSE_USER
        )

def clear_all_articles():
    """Удаляет все статьи из всех таблиц новостей."""
    client = get_clickhouse_client()
    
    try:
        print("🗑️  Начинаю удаление всех статей...")
        
        # Список всех таблиц новостей в схеме news
        news_tables = [
            'ria_headlines', 'lenta_headlines', 'rbc_headlines', 'gazeta_headlines', 
            'kommersant_headlines', 'tsn_headlines', 'unian_headlines', 'rt_headlines',
            'cnn_headlines', 'bbc_headlines', 'reuters_headlines', 'aljazeera_headlines',
            'dw_headlines', 'euronews_headlines', 'france24_headlines', 'israil_headlines',
            'telegram_ukraine', 'universal_europe', 'universal_usa', 'universal_other'
        ]
        
        # Категории для каждого источника
        categories = [
            'military_operations', 'humanitarian_crisis', 'economic_consequences',
            'political_decisions', 'information_social'
        ]
        
        # Источники с категориями
        sources_with_categories = [
            'ria', 'lenta', 'rbc', 'gazeta', 'kommersant', 
            'tsn', 'unian', 'rt', 'cnn', 'bbc', 'reuters', 
            'aljazeera', 'dw', 'euronews', 'france24', 'israil'
        ]
        
        total_deleted = 0
        
        # 1. Очищаем основные таблицы новостей
        print("\n📰 Очищаю основные таблицы новостей...")
        for table in news_tables:
            try:
                # Получаем количество записей перед удалением
                count_result = client.query(f"SELECT COUNT(*) FROM news.{table}")
                count = count_result.result_rows[0][0] if count_result.result_rows else 0
                
                if count > 0:
                    # Удаляем все записи
                    client.command(f"TRUNCATE TABLE news.{table}")
                    print(f"  ✅ {table}: удалено {count} записей")
                    total_deleted += count
                else:
                    print(f"  ⚪ {table}: таблица уже пуста")
                    
            except Exception as e:
                print(f"  ❌ Ошибка при очистке {table}: {e}")
        
        # 2. Очищаем таблицы категорий для каждого источника
        print("\n🏷️  Очищаю таблицы категорий...")
        for source in sources_with_categories:
            for category in categories:
                table_name = f"{source}_{category}"
                try:
                    count_result = client.query(f"SELECT COUNT(*) FROM news.{table_name}")
                    count = count_result.result_rows[0][0] if count_result.result_rows else 0
                    
                    if count > 0:
                        client.command(f"TRUNCATE TABLE news.{table_name}")
                        print(f"  ✅ {table_name}: удалено {count} записей")
                        total_deleted += count
                    else:
                        print(f"  ⚪ {table_name}: таблица уже пуста")
                        
                except Exception as e:
                    print(f"  ❌ Ошибка при очистке {table_name}: {e}")
        
        # 3. Очищаем таблицы украинского конфликта
        print("\n🇺🇦 Очищаю таблицы украинского конфликта...")
        ukraine_tables = ['all_news'] + categories
        
        for table in ukraine_tables:
            try:
                count_result = client.query(f"SELECT COUNT(*) FROM ukraine_conflict.{table}")
                count = count_result.result_rows[0][0] if count_result.result_rows else 0
                
                if count > 0:
                    client.command(f"TRUNCATE TABLE ukraine_conflict.{table}")
                    print(f"  ✅ ukraine_conflict.{table}: удалено {count} записей")
                    total_deleted += count
                else:
                    print(f"  ⚪ ukraine_conflict.{table}: таблица уже пуста")
                    
            except Exception as e:
                print(f"  ❌ Ошибка при очистке ukraine_conflict.{table}: {e}")
        
        # 4. Очищаем аналитические таблицы
        print("\n📊 Очищаю аналитические таблицы...")
        analytics_tables = ['daily_analytics', 'social_tension_metrics']
        
        for table in analytics_tables:
            try:
                count_result = client.query(f"SELECT COUNT(*) FROM ukraine_conflict.{table}")
                count = count_result.result_rows[0][0] if count_result.result_rows else 0
                
                if count > 0:
                    client.command(f"TRUNCATE TABLE ukraine_conflict.{table}")
                    print(f"  ✅ ukraine_conflict.{table}: удалено {count} записей")
                    total_deleted += count
                else:
                    print(f"  ⚪ ukraine_conflict.{table}: таблица уже пуста")
                    
            except Exception as e:
                print(f"  ❌ Ошибка при очистке ukraine_conflict.{table}: {e}")
        
        # 5. Очищаем пользовательские таблицы
        print("\n👤 Ищу и очищаю пользовательские таблицы...")
        try:
            custom_tables_result = client.query("""
                SELECT name FROM system.tables 
                WHERE database = 'news' 
                AND name LIKE 'custom_%_headlines'
                ORDER BY name
            """)
            
            for row in custom_tables_result.result_rows:
                table_name = row[0]
                try:
                    count_result = client.query(f"SELECT COUNT(*) FROM news.{table_name}")
                    count = count_result.result_rows[0][0] if count_result.result_rows else 0
                    
                    if count > 0:
                        client.command(f"TRUNCATE TABLE news.{table_name}")
                        print(f"  ✅ {table_name}: удалено {count} записей")
                        total_deleted += count
                    else:
                        print(f"  ⚪ {table_name}: таблица уже пуста")
                        
                except Exception as e:
                    print(f"  ❌ Ошибка при очистке {table_name}: {e}")
                    
        except Exception as e:
            print(f"  ❌ Ошибка при поиске пользовательских таблиц: {e}")
        
        print(f"\n🎉 Удаление завершено!")
        print(f"📊 Всего удалено записей: {total_deleted}")
        print(f"🔄 Счетчики статей обнулены")
        
        return total_deleted
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 0
        
    finally:
        client.close()

def main():
    """Главная функция."""
    print("🚨 ВНИМАНИЕ: Этот скрипт удалит ВСЕ статьи из базы данных!")
    print("Это действие необратимо!")
    
    # Запрашиваем подтверждение
    confirmation = input("\nВы уверены, что хотите продолжить? (введите 'ДА' для подтверждения): ")
    
    if confirmation.upper() != 'ДА':
        print("❌ Операция отменена пользователем")
        sys.exit(0)
    
    # Дополнительное подтверждение
    final_confirmation = input("\nПоследнее предупреждение! Введите 'УДАЛИТЬ ВСЕ' для окончательного подтверждения: ")
    
    if final_confirmation.upper() != 'УДАЛИТЬ ВСЕ':
        print("❌ Операция отменена пользователем")
        sys.exit(0)
    
    # Выполняем удаление
    deleted_count = clear_all_articles()
    
    if deleted_count > 0:
        print(f"\n✅ Успешно удалено {deleted_count} записей")
    else:
        print("\n⚪ Нет записей для удаления или произошла ошибка")

if __name__ == "__main__":
    main()