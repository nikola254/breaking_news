#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания таблиц аналитики с правильной структурой
"""

import sys
import os
from clickhouse_driver import Client

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

def create_analytics_tables():
    """Создает таблицы для аналитики с правильной структурой"""
    
    # Подключение к ClickHouse
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    print("🗄️ Создание таблиц для аналитики...")
    
    # Создаем базу данных если не существует
    try:
        client.execute('CREATE DATABASE IF NOT EXISTS news')
        print("✅ База данных 'news' готова")
    except Exception as e:
        print(f"❌ Ошибка создания базы данных: {e}")
        return False
    
    # Переключаемся на базу данных news
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database='news'
    )
    
    # Создаем основную таблицу для новостей с аналитикой
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS ukraine_headlines (
                id String,
                title String,
                content String,
                url String,
                source String,
                author String,
                date DateTime,
                category String,
                sentiment_score Float32,
                tension_score Float32,
                conflict_level Float32,
                urgency_factor Float32,
                emotional_intensity Float32,
                tension_category String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (date, category, id)
        '''
        client.execute(query)
        print("✅ Таблица ukraine_headlines создана")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы ukraine_headlines: {e}")
        return False
    
    # Создаем таблицу для Twitter данных
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS twitter_headlines (
                id String,
                title String,
                content String,
                url String,
                source String,
                author String,
                date DateTime,
                category String,
                sentiment_score Float32,
                tension_score Float32,
                conflict_level Float32,
                urgency_factor Float32,
                emotional_intensity Float32,
                tension_category String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (date, category, id)
        '''
        client.execute(query)
        print("✅ Таблица twitter_headlines создана")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы twitter_headlines: {e}")
        return False
    
    # Создаем таблицу для агрегированной аналитики
    try:
        query = '''
            CREATE TABLE IF NOT EXISTS analytics_summary (
                date Date,
                hour UInt8,
                category String,
                news_count UInt32,
                avg_sentiment Float32,
                avg_tension Float32,
                max_tension Float32,
                critical_count UInt32,
                high_count UInt32,
                medium_count UInt32,
                low_count UInt32,
                minimal_count UInt32,
                top_sources Array(String),
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (date, hour, category)
        '''
        client.execute(query)
        print("✅ Таблица analytics_summary создана")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы analytics_summary: {e}")
        return False
    
    # Создаем материализованное представление для автоматической агрегации
    try:
        query = '''
            CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_summary_mv TO analytics_summary AS
            SELECT 
                toDate(date) as date,
                toHour(date) as hour,
                category,
                count() as news_count,
                avg(sentiment_score) as avg_sentiment,
                avg(tension_score) as avg_tension,
                max(tension_score) as max_tension,
                countIf(tension_category = 'critical') as critical_count,
                countIf(tension_category = 'high') as high_count,
                countIf(tension_category = 'medium') as medium_count,
                countIf(tension_category = 'low') as low_count,
                countIf(tension_category = 'minimal') as minimal_count,
                groupArray(source) as top_sources,
                now() as created_at
            FROM ukraine_headlines
            GROUP BY date, hour, category
        '''
        client.execute(query)
        print("✅ Материализованное представление analytics_summary_mv создано")
    except Exception as e:
        print(f"❌ Ошибка создания представления: {e}")
    
    print("\n🎯 Все таблицы для аналитики созданы успешно!")
    return True

def main():
    """Основная функция"""
    print("🚀 Создание таблиц для аналитики")
    print("=" * 50)
    
    if create_analytics_tables():
        print("\n✅ Инициализация завершена успешно!")
        print("\n📋 Созданные таблицы:")
        print("• ukraine_headlines - основная таблица новостей")
        print("• twitter_headlines - таблица для Twitter данных")
        print("• analytics_summary - агрегированная аналитика")
        print("• analytics_summary_mv - автоматическая агрегация")
    else:
        print("\n❌ Ошибка при создании таблиц")

if __name__ == "__main__":
    main()