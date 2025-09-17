#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания новых таблиц базы данных для категорий украинского конфликта
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clickhouse_driver import Client
from config import Config
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ukraine_tables_creation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Новые категории украинского конфликта
UKRAINE_CATEGORIES = {
    'military_operations': 'Военные операции',
    'humanitarian_crisis': 'Гуманитарный кризис', 
    'economic_consequences': 'Экономические последствия',
    'political_decisions': 'Политические решения',
    'information_social': 'Информационно-социальные аспекты'
}

def create_ukraine_conflict_tables():
    """Создание таблиц для категорий украинского конфликта"""
    
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    try:
        # Удаляем существующие таблицы если есть
        try:
            client.execute('DROP DATABASE IF EXISTS ukraine_conflict')
            logger.info("Существующая база данных ukraine_conflict удалена")
        except Exception as e:
            logger.warning(f"Не удалось удалить базу данных: {e}")
        
        # Создаем базу данных заново
        client.execute('CREATE DATABASE ukraine_conflict')
        logger.info("База данных ukraine_conflict создана")
        
        # Создаем основную таблицу для всех новостей украинского конфликта
        main_table_query = """
        CREATE TABLE IF NOT EXISTS ukraine_conflict.all_news (
            id UInt64,
            title String,
            link String,
            content String,
            source String,
            category String,
            relevance_score Float32,
            keywords_found Array(String),
            published_date DateTime DEFAULT now(),
            created_at DateTime DEFAULT now(),
            sentiment_score Float32 DEFAULT 0.0,
            impact_level Enum8('low' = 1, 'medium' = 2, 'high' = 3) DEFAULT 'medium'
        ) ENGINE = MergeTree()
        ORDER BY (created_at, source, category)
        PARTITION BY toYYYYMM(created_at)
        """
        
        client.execute(main_table_query)
        logger.info("Основная таблица ukraine_conflict.all_news создана")
        
        # Создаем таблицы для каждой категории
        for category_key, category_name in UKRAINE_CATEGORIES.items():
            table_query = f"""
            CREATE TABLE IF NOT EXISTS ukraine_conflict.{category_key} (
                id UInt64,
                title String,
                link String,
                content String,
                source String,
                relevance_score Float32,
                keywords_found Array(String),
                published_date DateTime DEFAULT now(),
                created_at DateTime DEFAULT now(),
                sentiment_score Float32 DEFAULT 0.0,
                impact_level Enum8('low' = 1, 'medium' = 2, 'high' = 3) DEFAULT 'medium'
            ) ENGINE = MergeTree()
            ORDER BY (created_at, source)
            PARTITION BY toYYYYMM(created_at)
            """
            
            client.execute(table_query)
            logger.info(f"Таблица ukraine_conflict.{category_key} ({category_name}) создана")
        
        # Создаем таблицу для аналитики и агрегации
        analytics_table_query = """
        CREATE TABLE IF NOT EXISTS ukraine_conflict.daily_analytics (
            date Date,
            category String,
            source String,
            news_count UInt32,
            avg_relevance_score Float32,
            avg_sentiment_score Float32,
            high_impact_count UInt32,
            top_keywords Array(String)
        ) ENGINE = SummingMergeTree()
        ORDER BY (date, category, source)
        PARTITION BY toYYYYMM(date)
        """
        
        client.execute(analytics_table_query)
        logger.info("Таблица ukraine_conflict.daily_analytics создана")
        
        # Создаем материализованное представление для автоматической агрегации
        materialized_view_query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ukraine_conflict.daily_analytics_mv
        TO ukraine_conflict.daily_analytics
        AS SELECT
            toDate(created_at) as date,
            category,
            source,
            count() as news_count,
            avg(relevance_score) as avg_relevance_score,
            avg(sentiment_score) as avg_sentiment_score,
            countIf(impact_level = 'high') as high_impact_count,
            groupArray(arrayJoin(keywords_found)) as top_keywords
        FROM ukraine_conflict.all_news
        GROUP BY date, category, source
        """
        
        client.execute(materialized_view_query)
        logger.info("Материализованное представление ukraine_conflict.daily_analytics_mv создано")
        
        # Создаем таблицу для отслеживания социальной напряженности
        tension_table_query = """
        CREATE TABLE IF NOT EXISTS ukraine_conflict.social_tension_metrics (
            date Date,
            region String DEFAULT 'global',
            tension_level Float32,
            military_operations_impact Float32,
            humanitarian_crisis_impact Float32,
            economic_consequences_impact Float32,
            political_decisions_impact Float32,
            information_social_impact Float32,
            total_news_count UInt32,
            negative_sentiment_ratio Float32,
            created_at DateTime DEFAULT now()
        ) ENGINE = ReplacingMergeTree()
        ORDER BY (date, region)
        PARTITION BY toYYYYMM(date)
        """
        
        client.execute(tension_table_query)
        logger.info("Таблица ukraine_conflict.social_tension_metrics создана")
        
        logger.info("Все таблицы для украинского конфликта успешно созданы!")
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise
    finally:
        client.disconnect()

def show_tables_info():
    """Показать информацию о созданных таблицах"""
    
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    try:
        # Получаем список таблиц в базе ukraine_conflict
        tables = client.execute("SHOW TABLES FROM ukraine_conflict")
        
        logger.info("\n=== Созданные таблицы в базе ukraine_conflict ===")
        for table in tables:
            table_name = table[0]
            
            # Получаем информацию о структуре таблицы
            describe_result = client.execute(f"DESCRIBE ukraine_conflict.{table_name}")
            
            logger.info(f"\nТаблица: ukraine_conflict.{table_name}")
            logger.info("Структура:")
            for column in describe_result:
                logger.info(f"  {column[0]} - {column[1]}")
                
    except Exception as e:
        logger.error(f"Ошибка при получении информации о таблицах: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    logger.info("Начинаем создание таблиц для украинского конфликта...")
    
    create_ukraine_conflict_tables()
    show_tables_info()
    
    logger.info("\n=== Новые категории украинского конфликта ===")
    for key, name in UKRAINE_CATEGORIES.items():
        logger.info(f"{key}: {name}")
    
    logger.info("\nСоздание таблиц завершено успешно!")