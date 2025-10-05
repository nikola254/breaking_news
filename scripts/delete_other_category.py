"""
Скрипт для удаления всех статей с категорией 'other' из всех таблиц ClickHouse.
"""
import sys
import os

# Добавляем корневую директорию в путь для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clickhouse_driver import Client
from config import Config

def delete_other_category_articles():
    """Удаляет все статьи с категорией 'other' из всех таблиц."""
    
    print("="*60)
    print("УДАЛЕНИЕ СТАТЕЙ С КАТЕГОРИЕЙ 'OTHER'")
    print("="*60)
    
    # Подключаемся к ClickHouse
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Получаем список всех таблиц в базе news
    tables_query = """
        SELECT name 
        FROM system.tables 
        WHERE database = 'news' 
        AND name LIKE '%_headlines'
        OR name LIKE '%_military_operations'
        OR name LIKE '%_humanitarian_crisis'
        OR name LIKE '%_economic_consequences'
        OR name LIKE '%_political_decisions'
        OR name LIKE '%_information_social'
        OR name LIKE '%_other'
        ORDER BY name
    """
    
    result = client.execute(tables_query)
    tables = [row[0] for row in result]
    
    print(f"\nНайдено таблиц для проверки: {len(tables)}\n")
    
    total_deleted = 0
    
    for table_name in tables:
        try:
            # Проверяем, есть ли в таблице колонка category
            columns_query = f"DESCRIBE TABLE news.{table_name}"
            columns_result = client.execute(columns_query)
            columns = [row[0] for row in columns_result]
            
            if 'category' not in columns:
                print(f"⚠️  Таблица {table_name}: нет колонки 'category', пропускаем")
                continue
            
            # Считаем количество записей с category = 'other'
            count_query = f"SELECT COUNT(*) FROM news.{table_name} WHERE category = 'other'"
            count_result = client.execute(count_query)
            count = count_result[0][0]
            
            if count == 0:
                print(f"✓  Таблица {table_name}: нет записей с category='other'")
                continue
            
            # Удаляем записи с category = 'other'
            delete_query = f"ALTER TABLE news.{table_name} DELETE WHERE category = 'other'"
            client.execute(delete_query)
            
            print(f"🗑️  Таблица {table_name}: удалено {count} записей")
            total_deleted += count
            
        except Exception as e:
            print(f"❌ Ошибка при обработке таблицы {table_name}: {e}")
    
    print("\n" + "="*60)
    print(f"✅ Удаление завершено!")
    print(f"📊 Всего удалено записей: {total_deleted}")
    print("="*60)
    
    # Также удаляем старые категории из telegram_headlines
    print("\n" + "="*60)
    print("УДАЛЕНИЕ СТАРЫХ КАТЕГОРИЙ ИЗ TELEGRAM_HEADLINES")
    print("="*60)
    
    try:
        # Удаляем записи с category = 'military' (старая категория)
        old_military_query = "SELECT COUNT(*) FROM news.telegram_headlines WHERE category = 'military'"
        old_military_count = client.execute(old_military_query)[0][0]
        
        if old_military_count > 0:
            print(f"\n⚠️  Найдено {old_military_count} записей со старой категорией 'military'")
            print("   Эти записи будут удалены и пересозданы при следующем парсинге")
            
            delete_old_military = "ALTER TABLE news.telegram_headlines DELETE WHERE category = 'military'"
            client.execute(delete_old_military)
            print(f"🗑️  Удалено {old_military_count} записей с category='military'")
        
        # Удаляем записи с category = 'international' (старая категория)
        old_international_query = "SELECT COUNT(*) FROM news.telegram_headlines WHERE category = 'international'"
        old_international_count = client.execute(old_international_query)[0][0]
        
        if old_international_count > 0:
            print(f"\n⚠️  Найдено {old_international_count} записей со старой категорией 'international'")
            print("   Эти записи будут удалены и пересозданы при следующем парсинге")
            
            delete_old_international = "ALTER TABLE news.telegram_headlines DELETE WHERE category = 'international'"
            client.execute(delete_old_international)
            print(f"🗑️  Удалено {old_international_count} записей с category='international'")
        
        # Удаляем записи с category = 'other'
        other_query = "SELECT COUNT(*) FROM news.telegram_headlines WHERE category = 'other'"
        other_count = client.execute(other_query)[0][0]
        
        if other_count > 0:
            print(f"\n⚠️  Найдено {other_count} записей с категорией 'other'")
            
            delete_other = "ALTER TABLE news.telegram_headlines DELETE WHERE category = 'other'"
            client.execute(delete_other)
            print(f"🗑️  Удалено {other_count} записей с category='other'")
        
        print("\n✅ Очистка telegram_headlines завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке telegram_headlines: {e}")
    
    print("="*60)

if __name__ == '__main__':
    delete_other_category_articles()
