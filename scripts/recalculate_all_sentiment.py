"""
Скрипт для пересчета sentiment для всех существующих новостей в базе данных.
Обрабатывает новости пакетами для оптимизации производительности.
"""

import sys
import os

# Добавляем путь к корневой директории
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clickhouse_driver import Client
from config import Config
from app.utils.ukraine_sentiment_analyzer import get_ukraine_sentiment_analyzer
from tqdm import tqdm

def get_clickhouse_client():
    """Получение клиента ClickHouse"""
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )

def recalculate_sentiment_for_table(client, analyzer, table_name, batch_size=100):
    """
    Пересчитывает sentiment для всех новостей в таблице
    
    Args:
        client: ClickHouse клиент
        analyzer: Анализатор тональности
        table_name: Название таблицы
        batch_size: Размер пакета для обработки
    """
    try:
        # Получаем общее количество записей
        count_query = f"SELECT COUNT(*) FROM news.{table_name}"
        total_count = client.execute(count_query)[0][0]
        
        if total_count == 0:
            print(f"  ⚠️  Таблица {table_name} пуста, пропускаем")
            return 0
        
        print(f"  📊 Обработка {total_count} записей из {table_name}")
        
        # Обрабатываем пакетами
        processed = 0
        updated = 0
        
        with tqdm(total=total_count, desc=f"  {table_name}") as pbar:
            offset = 0
            while offset < total_count:
                # Получаем пакет записей
                query = f"""
                SELECT id, title, content
                FROM news.{table_name}
                LIMIT {batch_size} OFFSET {offset}
                """
                
                records = client.execute(query)
                
                if not records:
                    break
                
                # Обрабатываем каждую запись
                for record_id, title, content in records:
                    try:
                        # Анализируем тональность
                        text_for_analysis = f"{title or ''} {content or ''}"
                        
                        if text_for_analysis.strip():
                            sentiment_result = analyzer.analyze_sentiment(text_for_analysis)
                            
                            # Обновляем запись
                            update_query = f"""
                            ALTER TABLE news.{table_name}
                            UPDATE 
                                sentiment_score = {sentiment_result['sentiment_score']},
                                positive_score = {sentiment_result['positive_score']},
                                negative_score = {sentiment_result['negative_score']}
                            WHERE id = '{record_id}'
                            """
                            
                            client.execute(update_query)
                            updated += 1
                        
                        processed += 1
                        pbar.update(1)
                        
                    except Exception as e:
                        print(f"\n  ❌ Ошибка обработки записи {record_id}: {e}")
                        processed += 1
                        pbar.update(1)
                        continue
                
                offset += batch_size
        
        print(f"  ✅ Обработано: {processed}, Обновлено: {updated}")
        return updated
        
    except Exception as e:
        print(f"  ❌ Ошибка обработки таблицы {table_name}: {e}")
        return 0

def main():
    """Основная функция"""
    print("🚀 Запуск пересчета sentiment для всех новостей")
    print("=" * 60)
    
    # Инициализация
    client = get_clickhouse_client()
    analyzer = get_ukraine_sentiment_analyzer()
    
    # Получаем список всех таблиц
    tables_query = "SHOW TABLES FROM news"
    all_tables = [row[0] for row in client.execute(tables_query)]
    
    # Фильтруем таблицы (исключаем служебные)
    excluded_tables = [
        'monitoring_sessions',
        'news_sources_extremism_analysis',
        'social_analysis_results',
        'social_media_extremism_analysis',
        'telegram_channels_stats',
        'telegram_classification_analytics',
        'user_sources',
        'ok_posts',
        'vk_posts',
        'twitter_posts'
    ]
    
    news_tables = [t for t in all_tables if t not in excluded_tables and not t.endswith('_headlines')]
    
    print(f"\n📋 Найдено {len(news_tables)} таблиц для обработки")
    print("=" * 60)
    
    # Обрабатываем каждую таблицу
    total_updated = 0
    for i, table in enumerate(news_tables, 1):
        print(f"\n[{i}/{len(news_tables)}] Обработка таблицы: {table}")
        updated = recalculate_sentiment_for_table(client, analyzer, table)
        total_updated += updated
    
    print("\n" + "=" * 60)
    print(f"✅ Пересчет завершен!")
    print(f"📊 Всего обновлено записей: {total_updated}")
    print("=" * 60)

if __name__ == "__main__":
    main()
