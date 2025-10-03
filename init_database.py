#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания базы данных news и всех таблиц для парсеров новостей.
Используется для инициализации базы данных на новой машине.
"""

import sys
import os
from clickhouse_driver import Client

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

def create_main_tables(client):
    """Создает основные таблицы для каждого источника новостей"""
    
    # Список всех источников и их структур
    sources = {
        'ria': {
            'table': 'ria_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                source String DEFAULT 'ria.ru',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'israil': {
            'table': 'israil_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                source_links String,
                source String DEFAULT '7kanal.co.il',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'telegram': {
            'table': 'telegram_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                content String,
                channel String,
                message_id Int64,
                message_link String,
                source String DEFAULT 'telegram',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'lenta': {
            'table': 'lenta_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'lenta.ru',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'rbc': {
            'table': 'rbc_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'rbc.ru',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'cnn': {
            'table': 'cnn_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'cnn.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'aljazeera': {
            'table': 'aljazeera_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'aljazeera.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'tsn': {
            'table': 'tsn_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'tsn.ua',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'unian': {
            'table': 'unian_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'unian.net',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'rt': {
            'table': 'rt_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'rt.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'euronews': {
            'table': 'euronews_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'euronews.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'reuters': {
            'table': 'reuters_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'reuters.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'france24': {
            'table': 'france24_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'france24.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'dw': {
            'table': 'dw_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'dw.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'bbc': {
            'table': 'bbc_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'bbc.com',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'gazeta': {
            'table': 'gazeta_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'gazeta.ru',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        },
        'kommersant': {
            'table': 'kommersant_headlines',
            'structure': '''
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String,
                source String DEFAULT 'kommersant.ru',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            '''
        }
    }
    
    print("\nСоздание основных таблиц источников:")
    
    for source_name, source_info in sources.items():
        try:
            query = f'''
                CREATE TABLE IF NOT EXISTS news.{source_info["table"]} (
                    {source_info["structure"]}
                ) ENGINE = MergeTree()
                ORDER BY (published_date, id)
            '''
            
            client.execute(query)
            print(f"✓ Таблица {source_info['table']} создана")
            
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы {source_info['table']}: {e}")

def create_universal_tables(client):
    """Создает универсальные таблицы для парсера"""
    
    print("\nСоздание универсальных таблиц:")
    
    # Создаем основную универсальную таблицу
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS news.universal_news (
                id UUID DEFAULT generateUUIDv4(),
                site_name String,
                url String,
                title String,
                content String,
                category String,
                published_date DateTime DEFAULT now(),
                published_date DateTime DEFAULT now(),
                language String DEFAULT 'unknown',
                tags Array(String) DEFAULT [],
                metadata String DEFAULT '{}'
            ) ENGINE = MergeTree()
            ORDER BY (site_name, published_date)
        '''
        client.execute(query)
        print("✓ Таблица universal_news создана")
    except Exception as e:
        print(f"✗ Ошибка при создании таблицы universal_news: {e}")
    
    # Создаем универсальные таблицы категорий
    categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    
    for category in categories:
        try:
            query = f'''
                CREATE TABLE IF NOT EXISTS news.universal_{category} (
                    id UUID DEFAULT generateUUIDv4(),
                    title String,
                    link String,
                    content String,
                    source String,
                    category String DEFAULT '{category}',
                    published_date DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (published_date, id)
            '''
            client.execute(query)
            print(f"✓ Таблица universal_{category} создана")
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы universal_{category}: {e}")

def create_category_tables(client):
    """Создает таблицы для каждой категории новостей"""
    
    # Список категорий
    categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    
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
    
    print("\nСоздание таблиц категорий:")
    
    # Создаем таблицы для каждого источника и каждой категории
    for source_key, source_info in sources.items():
        for category in categories:
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
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                
                client.execute(query)
                print(f"✓ Таблица {source_info['table_suffix']}_{category} создана")
                
            except Exception as e:
                print(f"✗ Ошибка при создании таблицы {source_info['table_suffix']}_{category}: {e}")

def main():
    """Основная функция для инициализации базы данных"""
    print("=== Инициализация базы данных Breaking News ===")
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
    
    # Создаем основные таблицы
    create_main_tables(client)
    
    # Создаем таблицы категорий
    create_category_tables(client)
    
    # Создаем универсальные таблицы
    create_universal_tables(client)
    
    print("\n=== Инициализация завершена успешно! ===")
    print("\nСозданы:")
    print("• База данных 'news'")
    print("• 17 основных таблиц источников новостей")
    print("• 119 таблиц категорий (17 источников × 7 категорий)")
    print("• 8 универсальных таблиц (1 основная + 7 категорий)")
    print("\nТеперь вы можете запускать парсеры новостей!")

if __name__ == '__main__':
    main()
