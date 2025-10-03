#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единый скрипт для полной инициализации всех баз данных Breaking News
Создает все таблицы для новостей, социальных сетей, аналитики и прогнозирования
"""

import sys
import os
from clickhouse_driver import Client
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config


def create_databases(client):
    """Создает все необходимые базы данных"""
    logger.info("=== СОЗДАНИЕ БАЗ ДАННЫХ ===")
    
    databases = ['news', 'social_media']
    
    for db in databases:
        try:
            client.execute(f'CREATE DATABASE IF NOT EXISTS {db}')
            logger.info(f"✓ База данных '{db}' создана")
        except Exception as e:
            logger.error(f"✗ Ошибка при создании базы данных {db}: {e}")
            return False
    
    return True


def create_main_news_tables(client):
    """Создает основные таблицы источников новостей"""
    logger.info("\n=== СОЗДАНИЕ ОСНОВНЫХ ТАБЛИЦ ИСТОЧНИКОВ НОВОСТЕЙ ===")
    
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
    
    created_count = 0
    for source_name, source_info in sources.items():
        try:
            query = f'''
                CREATE TABLE IF NOT EXISTS news.{source_info["table"]} (
                    {source_info["structure"]}
                ) ENGINE = MergeTree()
                ORDER BY (published_date, id)
            '''
            client.execute(query)
            logger.info(f"✓ Таблица {source_info['table']} создана")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ Ошибка при создании таблицы {source_info['table']}: {e}")
    
    logger.info(f"Создано {created_count} из {len(sources)} основных таблиц")
    return created_count


def create_category_tables(client):
    """Создает таблицы категорий для всех источников"""
    logger.info("\n=== СОЗДАНИЕ ТАБЛИЦ КАТЕГОРИЙ ===")
    
    # Стандартные категории
    categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    
    # Расширенные категории для украинского конфликта
    ukraine_categories = [
        'military_operations',
        'humanitarian_crisis',
        'economic_consequences',
        'political_decisions',
        'information_social',
        'other'
    ]
    
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
    
    created_count = 0
    all_categories = list(set(categories + ukraine_categories))
    
    logger.info(f"Создание таблиц для {len(all_categories)} категорий и {len(sources)} источников...")
    
    for source_key, source_info in sources.items():
        for category in all_categories:
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
                created_count += 1
                
                # Логируем только каждую 10-ю таблицу, чтобы не загромождать вывод
                if created_count % 10 == 0:
                    logger.info(f"✓ Создано {created_count} таблиц категорий...")
                    
            except Exception as e:
                logger.error(f"✗ Ошибка при создании таблицы {source_info['table_suffix']}_{category}: {e}")
    
    logger.info(f"✓ Всего создано {created_count} таблиц категорий")
    return created_count


def create_universal_tables(client):
    """Создает универсальные таблицы"""
    logger.info("\n=== СОЗДАНИЕ УНИВЕРСАЛЬНЫХ ТАБЛИЦ ===")
    
    created_count = 0
    
    # Основная универсальная таблица
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
                language String DEFAULT 'unknown',
                tags Array(String) DEFAULT [],
                metadata String DEFAULT '{}'
            ) ENGINE = MergeTree()
            ORDER BY (site_name, published_date)
        '''
        client.execute(query)
        logger.info("✓ Таблица universal_news создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы universal_news: {e}")
    
    # Универсальная таблица для украинских новостей
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
        logger.info("✓ Таблица ukraine_universal_news создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы ukraine_universal_news: {e}")
    
    # Универсальные таблицы для стандартных категорий
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
            logger.info(f"✓ Таблица universal_{category} создана")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ Ошибка при создании таблицы universal_{category}: {e}")
    
    # Универсальные таблицы для украинских категорий
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
            logger.info(f"✓ Таблица ukraine_universal_{category} создана")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ Ошибка при создании таблицы ukraine_universal_{category}: {e}")
    
    logger.info(f"✓ Всего создано {created_count} универсальных таблиц")
    return created_count


def create_analytics_tables(client):
    """Создает таблицы для аналитики и прогнозирования"""
    logger.info("\n=== СОЗДАНИЕ АНАЛИТИЧЕСКИХ ТАБЛИЦ ===")
    
    created_count = 0
    
    # Таблица метрик социальной напряженности
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
            PARTITION BY toYYYYMM(date)
        '''
        client.execute(query)
        logger.info("✓ Таблица ukraine_social_tension_metrics создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы ukraine_social_tension_metrics: {e}")
    
    # Таблица прогнозов
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
            PARTITION BY toYYYYMM(prediction_date)
        '''
        client.execute(query)
        logger.info("✓ Таблица ukraine_tension_predictions создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы ukraine_tension_predictions: {e}")
    
    # Таблица ключевых событий
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
            PARTITION BY toYYYYMM(event_date)
        '''
        client.execute(query)
        logger.info("✓ Таблица ukraine_key_events создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы ukraine_key_events: {e}")
    
    # Таблица логов миграции
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
        logger.info("✓ Таблица migration_log создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы migration_log: {e}")
    
    logger.info(f"✓ Всего создано {created_count} аналитических таблиц")
    return created_count


def create_social_media_tables(client):
    """Создает таблицы для социальных сетей"""
    logger.info("\n=== СОЗДАНИЕ ТАБЛИЦ СОЦИАЛЬНЫХ СЕТЕЙ ===")
    
    created_count = 0
    
    # Таблица Twitter
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS social_media.twitter_posts (
                id String,
                text String,
                author_id String,
                author_username String,
                author_name String,
                created_at DateTime,
                public_metrics_retweet_count UInt32,
                public_metrics_like_count UInt32,
                public_metrics_reply_count UInt32,
                public_metrics_quote_count UInt32,
                lang String,
                possibly_sensitive UInt8,
                context_annotations Array(String),
                hashtags Array(String),
                mentions Array(String),
                urls Array(String),
                extremism_percentage Float32,
                risk_level String,
                analysis_method String,
                keywords_matched Array(String),
                published_date DateTime DEFAULT now(),
                source String DEFAULT 'twitter'
            ) ENGINE = MergeTree()
            ORDER BY (created_at, id)
            PARTITION BY toYYYYMM(created_at)
        '''
        client.execute(query)
        logger.info("✓ Таблица social_media.twitter_posts создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы twitter_posts: {e}")
    
    # Таблица VK
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS social_media.vk_posts (
                id String,
                owner_id String,
                from_id String,
                text String,
                date DateTime,
                post_type String,
                attachments Array(String),
                comments_count UInt32,
                likes_count UInt32,
                reposts_count UInt32,
                views_count UInt32,
                is_pinned UInt8,
                marked_as_ads UInt8,
                geo_place String,
                signer_id String,
                copy_history Array(String),
                extremism_percentage Float32,
                risk_level String,
                analysis_method String,
                keywords_matched Array(String),
                published_date DateTime DEFAULT now(),
                source String DEFAULT 'vk'
            ) ENGINE = MergeTree()
            ORDER BY (date, id)
            PARTITION BY toYYYYMM(date)
        '''
        client.execute(query)
        logger.info("✓ Таблица social_media.vk_posts создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы vk_posts: {e}")
    
    # Таблица OK
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS social_media.ok_posts (
                id String,
                author_id String,
                author_name String,
                text String,
                created_time DateTime,
                media Array(String),
                likes_count UInt32,
                comments_count UInt32,
                reshares_count UInt32,
                group_id String,
                group_name String,
                post_type String,
                link_url String,
                link_title String,
                extremism_percentage Float32,
                risk_level String,
                analysis_method String,
                keywords_matched Array(String),
                published_date DateTime DEFAULT now(),
                source String DEFAULT 'ok'
            ) ENGINE = MergeTree()
            ORDER BY (created_time, id)
            PARTITION BY toYYYYMM(created_time)
        '''
        client.execute(query)
        logger.info("✓ Таблица social_media.ok_posts создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы ok_posts: {e}")
    
    # Таблица Telegram для социальных сетей
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS social_media.telegram_posts (
                id String,
                channel_id String,
                channel_username String,
                channel_title String,
                message_id UInt32,
                text String,
                date DateTime,
                views UInt32,
                forwards UInt32,
                replies UInt32,
                media_type String,
                media_url String,
                has_links UInt8,
                links Array(String),
                extremism_percentage Float32,
                risk_level String,
                analysis_method String,
                keywords_matched Array(String),
                published_date DateTime DEFAULT now(),
                source String DEFAULT 'telegram'
            ) ENGINE = MergeTree()
            ORDER BY (date, id)
            PARTITION BY toYYYYMM(date)
        '''
        client.execute(query)
        logger.info("✓ Таблица social_media.telegram_posts создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы telegram_posts: {e}")
    
    # Общая таблица всех постов
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS social_media.all_posts (
                id String,
                platform String,
                author_id String,
                author_name String,
                text String,
                created_at DateTime,
                engagement_metrics String,
                extremism_percentage Float32,
                risk_level String,
                analysis_method String,
                keywords_matched Array(String),
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (created_at, platform, id)
            PARTITION BY (platform, toYYYYMM(created_at))
        '''
        client.execute(query)
        logger.info("✓ Таблица social_media.all_posts создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы all_posts: {e}")
    
    # Таблица статистики парсинга
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS social_media.parsing_stats (
                id String,
                platform String,
                start_time DateTime,
                end_time DateTime,
                total_posts UInt32,
                extremist_posts UInt32,
                keywords Array(String),
                status String,
                error_message String,
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (start_time, platform)
            PARTITION BY toYYYYMM(start_time)
        '''
        client.execute(query)
        logger.info("✓ Таблица social_media.parsing_stats создана")
        created_count += 1
    except Exception as e:
        logger.error(f"✗ Ошибка при создании таблицы parsing_stats: {e}")
    
    logger.info(f"✓ Всего создано {created_count} таблиц социальных сетей")
    return created_count


def log_initialization(client):
    """Записывает информацию об инициализации в лог"""
    try:
        client.execute(
            "INSERT INTO news.migration_log (migration_name, status, details) VALUES",
            [('unified_database_initialization', 'completed', 
              f'Полная инициализация базы данных завершена {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')]
        )
    except Exception as e:
        logger.warning(f"Не удалось записать лог инициализации: {e}")


def main():
    """Основная функция для полной инициализации всех баз данных"""
    print("=" * 80)
    print("ЕДИНАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ BREAKING NEWS")
    print("=" * 80)
    print(f"\nПодключение к ClickHouse: {Config.CLICKHOUSE_HOST}:{Config.CLICKHOUSE_NATIVE_PORT}")
    print(f"Пользователь: {Config.CLICKHOUSE_USER}")
    
    try:
        # Подключаемся к ClickHouse
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        logger.info("✓ Подключение к ClickHouse установлено")
        
        # Создаем базы данных
        if not create_databases(client):
            logger.error("Не удалось создать базы данных. Завершение работы.")
            return
        
        # Переключаемся на базу news для создания таблиц
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database='news'
        )
        
        # Создаем все таблицы
        main_tables = create_main_news_tables(client)
        category_tables = create_category_tables(client)
        universal_tables = create_universal_tables(client)
        analytics_tables = create_analytics_tables(client)
        social_tables = create_social_media_tables(client)
        
        # Записываем лог инициализации
        log_initialization(client)
        
        # Итоговая статистика
        print("\n" + "=" * 80)
        print("ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 80)
        print("\n[СТАТИСТИКА] СОЗДАННЫЕ ОБЪЕКТЫ:")
        print(f"  - Базы данных: 2 (news, social_media)")
        print(f"  - Основные таблицы источников: {main_tables}")
        print(f"  - Таблицы категорий: {category_tables}")
        print(f"  - Универсальные таблицы: {universal_tables}")
        print(f"  - Аналитические таблицы: {analytics_tables}")
        print(f"  - Таблицы социальных сетей: {social_tables}")
        print(f"\n  ВСЕГО ТАБЛИЦ: {main_tables + category_tables + universal_tables + analytics_tables + social_tables}")
        
        print("\n[КАТЕГОРИИ] НОВОСТЕЙ:")
        print("  Стандартные: ukraine, middle_east, fake_news, info_war, europe, usa, other")
        print("  Украинский конфликт: military_operations, humanitarian_crisis,")
        print("                       economic_consequences, political_decisions,")
        print("                       information_social, other")
        
        print("\n[ИСТОЧНИКИ] НОВОСТЕЙ:")
        print("  RIA, Lenta, RBC, Telegram, CNN, Al Jazeera, TSN, Unian, RT,")
        print("  EuroNews, Reuters, France24, DW, BBC, Gazeta, Kommersant, Israil")
        
        print("\n[СЛЕДУЮЩИЕ ШАГИ]:")
        print("  1. Запустите парсеры новостей для сбора данных")
        print("  2. Используйте аналитические таблицы для прогнозирования")
        print("  3. Мониторьте социальные сети через social_media базу")
        print("  4. Просматривайте логи в таблице news.migration_log")
        print("\n[OK] Система готова к работе!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"✗ Критическая ошибка при инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            client.disconnect()
        except:
            pass
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

