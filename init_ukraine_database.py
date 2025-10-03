#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания базы данных news с новыми таблицами для украинского конфликта.
Используется для миграции на новую структуру категорий.
"""

import sys
import os
from clickhouse_driver import Client
from datetime import datetime

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config

def create_database():
    """Создает базу данных news"""
    try:
        # Подключаемся к ClickHouse без указания базы данных
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Создаем базу данных
        client.execute('CREATE DATABASE IF NOT EXISTS news')
        print("✓ База данных 'news' создана успешно")
        
        return client
    except Exception as e:
        print(f"✗ Ошибка при создании базы данных: {e}")
        return None

def create_ukraine_category_tables(client):
    """Создает таблицы для новых категорий украинского конфликта"""
    
    # Новые категории украинского конфликта
    ukraine_categories = [
        'military_operations',      # Военные операции
        'humanitarian_crisis',      # Гуманитарный кризис
        'economic_consequences',    # Экономические последствия
        'political_decisions',      # Политические решения
        'information_social',       # Информационно-социальные аспекты
        'other'                     # Прочее (нерелевантные новости)
    ]
    
    # Список всех источников новостей
    sources = {
        'ria': {'table_suffix': 'ria', 'default_source': 'ria.ru'},
        'israil': {'table_suffix': 'israil', 'default_source': '7kanal.co.il'},
        'telegram': {'table_suffix': 'telegram', 'default_source': 'telegram'},
        'lenta': {'table_suffix': 'lenta', 'default_source': 'lenta.ru'},
        'rbc': {'table_suffix': 'rbc', 'default_source': 'rbc.ru'},
        'cnn': {'table_suffix': 'cnn', 'default_source': 'cnn.com'},
        'aljazeera': {'table_suffix': 'aljazeera', 'default_source': 'aljazeera.com'},
        'tsn': {'table_suffix': 'tsn', 'default_source': 'tsn.ua'},
        'unian': {'table_suffix': 'unian', 'default_source': 'unian.net'},
        'rt': {'table_suffix': 'rt', 'default_source': 'rt.com'},
        'euronews': {'table_suffix': 'euronews', 'default_source': 'euronews.com'},
        'reuters': {'table_suffix': 'reuters', 'default_source': 'reuters.com'},
        'france24': {'table_suffix': 'france24', 'default_source': 'france24.com'},
        'dw': {'table_suffix': 'dw', 'default_source': 'dw.com'},
        'bbc': {'table_suffix': 'bbc', 'default_source': 'bbc.com'},
        'gazeta': {'table_suffix': 'gazeta', 'default_source': 'gazeta.ru'},
        'kommersant': {'table_suffix': 'kommersant', 'default_source': 'kommersant.ru'}
    }
    
    print("\nСоздание таблиц для украинских категорий:")
    
    # Создаем таблицы для каждого источника и каждой украинской категории
    for source_key, source_info in sources.items():
        for category in ukraine_categories:
            try:
                # Специальная обработка для telegram
                if source_key == 'telegram':
                    query = f'''
                        CREATE TABLE IF NOT EXISTS news.telegram_{category} (
                            id UUID DEFAULT generateUUIDv4(),
                            title String,
                            content String,
                            channel String,
                            message_id Int64,
                            message_link String,
                            source String DEFAULT 'telegram',
                            category String DEFAULT '{category}',
                            relevance_score Float32 DEFAULT 0.0,
                            ai_confidence Float32 DEFAULT 0.0,
                            keywords_found Array(String) DEFAULT [],
                            sentiment_score Float32 DEFAULT 0.0,
                            tension_score Float32 DEFAULT 0.0,
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                # Специальная обработка для israil
                elif source_key == 'israil':
                    query = f'''
                        CREATE TABLE IF NOT EXISTS news.israil_{category} (
                            id UUID DEFAULT generateUUIDv4(),
                            title String,
                            link String,
                            content String,
                            source_links String,
                            source String DEFAULT '7kanal.co.il',
                            category String DEFAULT '{category}',
                            relevance_score Float32 DEFAULT 0.0,
                            ai_confidence Float32 DEFAULT 0.0,
                            keywords_found Array(String) DEFAULT [],
                            sentiment_score Float32 DEFAULT 0.0,
                            tension_score Float32 DEFAULT 0.0,
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                # Стандартная структура для остальных источников
                else:
                    query = f'''
                        CREATE TABLE IF NOT EXISTS news.{source_info["table_suffix"]}_{category} (
                            id UUID DEFAULT generateUUIDv4(),
                            title String,
                            link String,
                            content String,
                            source String DEFAULT '{source_info["default_source"]}',
                            category String DEFAULT '{category}',
                            relevance_score Float32 DEFAULT 0.0,
                            ai_confidence Float32 DEFAULT 0.0,
                            keywords_found Array(String) DEFAULT [],
                            sentiment_score Float32 DEFAULT 0.0,
                            tension_score Float32 DEFAULT 0.0,
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                
                client.execute(query)
                print(f"✓ Таблица {source_info['table_suffix']}_{category} создана")
                
            except Exception as e:
                print(f"✗ Ошибка при создании таблицы {source_info['table_suffix']}_{category}: {e}")

def create_ukraine_universal_tables(client):
    """Создает универсальные таблицы для украинских категорий"""
    
    print("\nСоздание универсальных таблиц для украинского конфликта:")
    
    # Создаем основную универсальную таблицу для украинских новостей
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS news.ukraine_universal_news (
                id UUID DEFAULT generateUUIDv4(),
                site_name String,
                url String,
                title String,
                content String,
                category String,
                relevance_score Float32 DEFAULT 0.0,
                ai_confidence Float32 DEFAULT 0.0,
                keywords_found Array(String) DEFAULT [],
                sentiment_score Float32 DEFAULT 0.0,
                tension_score Float32 DEFAULT 0.0,
                published_date DateTime DEFAULT now(),
                language String DEFAULT 'unknown',
                tags Array(String) DEFAULT [],
                metadata String DEFAULT '{}'
            ) ENGINE = MergeTree()
            ORDER BY (site_name, published_date)
        '''
        client.execute(query)
        print("✓ Таблица ukraine_universal_news создана")
    except Exception as e:
        print(f"✗ Ошибка при создании таблицы ukraine_universal_news: {e}")
    
    # Создаем универсальные таблицы для каждой украинской категории
    ukraine_categories = [
        'military_operations',
        'humanitarian_crisis', 
        'economic_consequences',
        'political_decisions',
        'information_social',
        'other'
    ]
    
    for category in ukraine_categories:
        try:
            query = f'''
                CREATE TABLE IF NOT EXISTS news.ukraine_universal_{category} (
                    id UUID DEFAULT generateUUIDv4(),
                    title String,
                    link String,
                    content String,
                    source String,
                    category String DEFAULT '{category}',
                    relevance_score Float32 DEFAULT 0.0,
                    ai_confidence Float32 DEFAULT 0.0,
                    keywords_found Array(String) DEFAULT [],
                    sentiment_score Float32 DEFAULT 0.0,
                    tension_score Float32 DEFAULT 0.0,
                    published_date DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (published_date, id)
            '''
            client.execute(query)
            print(f"✓ Таблица ukraine_universal_{category} создана")
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы ukraine_universal_{category}: {e}")

def create_analytics_tables(client):
    """Создает таблицы для аналитики и прогнозирования"""
    
    print("\nСоздание аналитических таблиц:")
    
    # Таблица для хранения метрик социальной напряженности
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS news.ukraine_social_tension_metrics (
                id UUID DEFAULT generateUUIDv4(),
                date Date,
                hour UInt8,
                category String,
                news_count UInt32,
                avg_sentiment Float32,
                tension_score Float32,
                keywords_frequency Map(String, UInt32),
                sources_distribution Map(String, UInt32),
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (date, hour, category)
        '''
        client.execute(query)
        print("✓ Таблица ukraine_social_tension_metrics создана")
    except Exception as e:
        print(f"✗ Ошибка при создании таблицы ukraine_social_tension_metrics: {e}")
    
    # Таблица для хранения прогнозов
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS news.ukraine_tension_predictions (
                id UUID DEFAULT generateUUIDv4(),
                prediction_date Date,
                prediction_hour UInt8,
                category String,
                predicted_tension Float32,
                confidence_interval_low Float32,
                confidence_interval_high Float32,
                model_version String,
                features_used Array(String),
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (prediction_date, prediction_hour, category)
        '''
        client.execute(query)
        print("✓ Таблица ukraine_tension_predictions создана")
    except Exception as e:
        print(f"✗ Ошибка при создании таблицы ukraine_tension_predictions: {e}")
    
    # Таблица для хранения ключевых событий
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS news.ukraine_key_events (
                id UUID DEFAULT generateUUIDv4(),
                event_date DateTime,
                category String,
                event_title String,
                event_description String,
                impact_score Float32,
                related_news_ids Array(String),
                sources Array(String),
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (event_date, category)
        '''
        client.execute(query)
        print("✓ Таблица ukraine_key_events создана")
    except Exception as e:
        print(f"✗ Ошибка при создании таблицы ukraine_key_events: {e}")

def create_migration_log_table(client):
    """Создает таблицу для логирования миграции"""
    
    print("\nСоздание таблицы логов миграции:")
    
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS news.migration_log (
                id UUID DEFAULT generateUUIDv4(),
                migration_name String,
                migration_date DateTime DEFAULT now(),
                status String,
                details String,
                affected_tables Array(String),
                records_migrated UInt64 DEFAULT 0
            ) ENGINE = MergeTree()
            ORDER BY migration_date
        '''
        client.execute(query)
        print("✓ Таблица migration_log создана")
        
        # Записываем информацию о текущей миграции
        client.execute(
            "INSERT INTO news.migration_log (migration_name, status, details) VALUES",
            [('ukraine_categories_migration', 'started', 'Создание новых таблиц для украинских категорий')]
        )
        
    except Exception as e:
        print(f"✗ Ошибка при создании таблицы migration_log: {e}")

def backup_old_tables(client):
    """Создает резервные копии старых таблиц"""
    
    print("\nСоздание резервных копий старых таблиц:")
    
    old_categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    sources = ['ria', 'lenta', 'rbc', 'telegram', 'cnn', 'aljazeera', 'tsn', 'unian', 'rt', 
               'euronews', 'reuters', 'france24', 'dw', 'bbc', 'gazeta', 'kommersant', 'israil']
    
    backup_date = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for source in sources:
        for category in old_categories:
            try:
                # Проверяем, существует ли таблица
                check_query = f"EXISTS TABLE news.{source}_{category}"
                exists = client.execute(check_query)[0][0]
                
                if exists:
                    # Создаем резервную копию
                    backup_query = f'''
                        CREATE TABLE IF NOT EXISTS news.backup_{backup_date}_{source}_{category}
                        AS news.{source}_{category}
                    '''
                    client.execute(backup_query)
                    print(f"✓ Резервная копия backup_{backup_date}_{source}_{category} создана")
                    
            except Exception as e:
                print(f"✗ Ошибка при создании резервной копии {source}_{category}: {e}")

def main():
    """Основная функция для инициализации базы данных с украинскими категориями"""
    print("=== Инициализация базы данных для украинского конфликта ===")
    print(f"Подключение к ClickHouse: {Config.CLICKHOUSE_HOST}:{Config.CLICKHOUSE_NATIVE_PORT}")
    
    # Создаем базу данных
    client = create_database()
    if not client:
        print("\n✗ Не удалось создать базу данных. Завершение работы.")
        return
    
    # Переключаемся на созданную базу данных
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database='news'
    )
    
    # Создаем таблицу логов миграции
    create_migration_log_table(client)
    
    # Создаем резервные копии старых таблиц
    backup_old_tables(client)
    
    # Создаем таблицы для украинских категорий
    create_ukraine_category_tables(client)
    
    # Создаем универсальные таблицы для украинских категорий
    create_ukraine_universal_tables(client)
    
    # Создаем аналитические таблицы
    create_analytics_tables(client)
    
    # Обновляем лог миграции
    try:
        client.execute(
            "INSERT INTO news.migration_log (migration_name, status, details, affected_tables) VALUES",
            [('ukraine_categories_migration', 'completed', 
              'Успешно созданы все таблицы для украинских категорий',
              ['ukraine_category_tables', 'ukraine_universal_tables', 'analytics_tables'])]
        )
    except Exception as e:
        print(f"Ошибка при обновлении лога миграции: {e}")
    
    print("\n=== Инициализация завершена успешно! ===")
    print("\nСозданы:")
    print("• База данных 'news'")
    print("• 102 таблицы для украинских категорий (17 источников × 6 категорий)")
    print("• 7 универсальных таблиц для украинского конфликта")
    print("• 3 аналитические таблицы для прогнозирования")
    print("• 1 таблица логов миграции")
    print("• Резервные копии старых таблиц")
    print("\nНовые категории:")
    print("• military_operations - Военные операции")
    print("• humanitarian_crisis - Гуманитарный кризис")
    print("• economic_consequences - Экономические последствия")
    print("• political_decisions - Политические решения")
    print("• information_social - Информационно-социальные аспекты")
    print("• other - Прочее")
    print("\nТеперь можно запускать парсеры с новой системой категорий!")

if __name__ == '__main__':
    main()
