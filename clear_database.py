"""
Скрипт для очистки всех данных из таблиц ClickHouse
"""
from app.models import get_clickhouse_client

def clear_all_tables():
    """Очищает все таблицы в базе данных news"""
    
    # Список всех таблиц для очистки
    tables = [
        # Основные таблицы новостей
        'ria_headlines',
        'israil_headlines',
        'lenta_headlines',
        'rbc_headlines',
        'cnn_headlines',
        'aljazeera_headlines',
        'tsn_headlines',
        'unian_headlines',
        'rt_headlines',
        'euronews_headlines',
        'reuters_headlines',
        'france24_headlines',
        'dw_headlines',
        'bbc_headlines',
        'gazeta_headlines',
        'kommersant_headlines',
        
        # Universal таблицы
        'universal_military_operations',
        'universal_humanitarian_crisis',
        'universal_economic_consequences',
        'universal_political_decisions',
        'universal_information_social',
        
        # Telegram таблицы
        'telegram_military_operations',
        'telegram_humanitarian_crisis',
        'telegram_economic_consequences',
        'telegram_political_decisions',
        'telegram_information_social',
        'telegram_headlines',
        
        # Социальные сети
        'twitter_posts',
        'vk_posts',
        'ok_posts',
        'telegram_posts',
        
        # Аналитические таблицы
        'telegram_channels_stats',
        'telegram_classification_analytics',
        'telegram_messages_classified',
        'social_media_extremism_analysis',
        'news_sources_extremism_analysis',
    ]
    
    client = get_clickhouse_client()
    
    try:
        print("=" * 60)
        print("ОЧИСТКА БАЗЫ ДАННЫХ CLICKHOUSE")
        print("=" * 60)
        
        # Получаем список всех существующих таблиц
        result = client.query("SELECT name FROM system.tables WHERE database = 'news'")
        existing_tables = [row[0] for row in result.result_rows]
        
        print(f"\nНайдено {len(existing_tables)} таблиц в базе данных 'news'")
        
        # Очищаем каждую таблицу
        cleared_count = 0
        skipped_count = 0
        error_count = 0
        
        for table in tables:
            if table not in existing_tables:
                print(f"⊘ Таблица '{table}' не существует - пропускаем")
                skipped_count += 1
                continue
            
            try:
                # Получаем количество записей до очистки
                count_query = f"SELECT COUNT(*) FROM news.{table}"
                count_result = client.query(count_query)
                records_before = count_result.result_rows[0][0]
                
                if records_before == 0:
                    print(f"○ Таблица '{table}' уже пуста")
                    cleared_count += 1
                    continue
                
                # Очищаем таблицу
                truncate_query = f"TRUNCATE TABLE IF EXISTS news.{table}"
                client.query(truncate_query)
                
                print(f"✓ Таблица '{table}' очищена ({records_before:,} записей удалено)")
                cleared_count += 1
                
            except Exception as e:
                print(f"✗ Ошибка при очистке таблицы '{table}': {str(e)}")
                error_count += 1
        
        # Также очищаем все пользовательские таблицы (custom_%)
        custom_tables_query = """
            SELECT name FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
        """
        custom_result = client.query(custom_tables_query)
        custom_tables = [row[0] for row in custom_result.result_rows]
        
        if custom_tables:
            print(f"\nНайдено {len(custom_tables)} пользовательских таблиц:")
            for table in custom_tables:
                try:
                    count_query = f"SELECT COUNT(*) FROM news.{table}"
                    count_result = client.query(count_query)
                    records_before = count_result.result_rows[0][0]
                    
                    if records_before > 0:
                        truncate_query = f"TRUNCATE TABLE IF EXISTS news.{table}"
                        client.query(truncate_query)
                        print(f"✓ Таблица '{table}' очищена ({records_before:,} записей удалено)")
                        cleared_count += 1
                    else:
                        print(f"○ Таблица '{table}' уже пуста")
                        cleared_count += 1
                        
                except Exception as e:
                    print(f"✗ Ошибка при очистке таблицы '{table}': {str(e)}")
                    error_count += 1
        
        print("\n" + "=" * 60)
        print("ИТОГИ:")
        print(f"  Очищено таблиц: {cleared_count}")
        print(f"  Пропущено таблиц: {skipped_count}")
        print(f"  Ошибок: {error_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()
        print("\nБаза данных очищена!")


if __name__ == '__main__':
    import sys
    
    # Запрашиваем подтверждение
    print("\n⚠️  ВНИМАНИЕ! ⚠️")
    print("Этот скрипт удалит ВСЕ данные из всех таблиц базы данных ClickHouse!")
    print("Это действие НЕОБРАТИМО!\n")
    
    response = input("Вы уверены, что хотите продолжить? (введите 'ДА' для подтверждения): ")
    
    if response.strip().upper() == 'ДА':
        clear_all_tables()
    else:
        print("\n✓ Операция отменена")
        sys.exit(0)


