#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексный скрипт для создания полноценных тестовых данных аналитики
Создает реалистичные данные для всех графиков и показателей
"""

import sys
import os
from datetime import datetime, timedelta
import random
import json
from clickhouse_driver import Client

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

def create_comprehensive_analytics():
    """Создает комплексные тестовые данные для полной демонстрации аналитики"""
    
    # Подключение к ClickHouse
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )
    
    print("🚀 Создание комплексных тестовых данных для аналитики...")
    
    # Очистка старых тестовых данных
    print("🧹 Очистка старых тестовых данных...")
    try:
        client.execute("DELETE FROM ukraine_headlines WHERE id LIKE 'test_comprehensive_%'")
        print("✅ Старые тестовые данные удалены")
    except Exception as e:
        print(f"⚠️ Ошибка при очистке: {e}")
    
    # Создание новостных данных
    create_news_data(client)
    
    print("🎉 Комплексные тестовые данные созданы успешно!")

def create_news_data(client):
    """Создает разнообразные новостные данные"""
    print("📰 Создание новостных данных...")
    
    categories = [
        'test_military', 'test_diplomatic', 'test_economic', 'test_humanitarian', 'test_information',
        'test_political', 'test_social', 'test_international', 'test_security', 'test_technology'
    ]
    
    sources = [
        'test_bbc', 'test_cnn', 'test_reuters', 'test_ap', 'test_guardian',
        'test_france24', 'test_dw', 'test_euronews', 'test_aljazeera', 'test_rt'
    ]
    
    # Генерируем данные за последние 30 дней
    base_date = datetime.now() - timedelta(days=30)
    
    news_data = []
    for i in range(500):  # 500 новостей
        date = base_date + timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        category = random.choice(categories)
        source = random.choice(sources)
        
        # Генерируем реалистичные показатели
        sentiment_score = round(random.uniform(0.0, 1.0), 3)
        tension_score = round(random.uniform(0.0, 1.0), 3)
        conflict_level = round(random.uniform(0.0, 1.0), 3)
        urgency_factor = round(random.uniform(0.0, 1.0), 3)
        emotional_intensity = round(random.uniform(0.0, 1.0), 3)
        
        # Определяем категорию напряженности
        if tension_score >= 0.8:
            tension_category = 'critical'
        elif tension_score >= 0.6:
            tension_category = 'high'
        elif tension_score >= 0.4:
            tension_category = 'medium'
        elif tension_score >= 0.2:
            tension_category = 'low'
        else:
            tension_category = 'minimal'
        
        # Создаем заголовки в зависимости от категории
        titles = {
            'test_military': [
                'Военные учения в регионе',
                'Поставки военной техники',
                'Анализ военной ситуации',
                'Стратегические операции'
            ],
            'test_diplomatic': [
                'Дипломатические переговоры',
                'Международные соглашения',
                'Визит делегации',
                'Мирные инициативы'
            ],
            'test_economic': [
                'Экономические санкции',
                'Торговые отношения',
                'Финансовая помощь',
                'Энергетический кризис'
            ],
            'test_humanitarian': [
                'Гуманитарная помощь',
                'Беженцы и переселенцы',
                'Медицинская помощь',
                'Восстановление инфраструктуры'
            ],
            'test_information': [
                'Информационная война',
                'Кибератаки',
                'Пропаганда в СМИ',
                'Дезинформация'
            ]
        }
        
        title = random.choice(titles.get(category, ['Общие новости']))
        content = f"Подробное содержание новости о {title.lower()}. " * 5
        
        news_data.append([
            f"test_comprehensive_{i}",  # id (String)
            title,  # title
            content,  # content
            f'https://test-source.com/news/{i}',  # url
            source,  # source
            f'test_author_{i % 10}',  # author
            date,  # date
            category,  # category
            sentiment_score,  # sentiment_score
            tension_score,  # tension_score
            conflict_level,  # conflict_level
            urgency_factor,  # urgency_factor
            emotional_intensity,  # emotional_intensity
            tension_category,  # tension_category
            datetime.now()  # created_at
        ])
    
    # Вставляем данные
    client.execute("""
        INSERT INTO ukraine_headlines 
        (id, title, content, url, source, author, date, category, 
         sentiment_score, tension_score, conflict_level, urgency_factor, 
         emotional_intensity, tension_category, created_at)
        VALUES
    """, news_data)
    
    print(f"✅ Создано {len(news_data)} новостных записей")

def create_social_media_data(client):
    """Создает данные социальных сетей"""
    print("📱 Создание данных социальных сетей...")
    
    platforms = ['test_telegram', 'test_twitter', 'test_vk', 'test_ok']
    risk_levels = ['low', 'medium', 'high', 'critical']
    
    # Генерируем данные за последние 7 дней
    base_date = datetime.now() - timedelta(days=7)
    
    social_data = []
    for i in range(200):  # 200 постов
        date = base_date + timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        platform = random.choice(platforms)
        risk_level = random.choice(risk_levels)
        
        # Генерируем показатели экстремизма
        if risk_level == 'low':
            extremism_percentage = round(random.uniform(0, 25), 1)
        elif risk_level == 'medium':
            extremism_percentage = round(random.uniform(25, 50), 1)
        elif risk_level == 'high':
            extremism_percentage = round(random.uniform(50, 75), 1)
        else:  # critical
            extremism_percentage = round(random.uniform(75, 100), 1)
        
        keywords_matched = random.randint(1, 10)
        
        social_data.append([
            i + 1,  # id
            platform,
            f'test_user_{i}',  # author_name
            f'Тестовый пост #{i} с различным содержанием для анализа',  # text
            date,
            extremism_percentage,
            risk_level,
            keywords_matched
        ])
    
    # Вставляем данные в общую таблицу
    client.execute("""
        INSERT INTO social_media.all_posts 
        (id, platform, author_name, text, created_at, extremism_percentage, risk_level, keywords_matched)
        VALUES
    """, social_data)
    
    # Создаем специфичные данные для каждой платформы
    create_platform_specific_data(client)
    
    print(f"✅ Создано {len(social_data)} записей социальных сетей")

def create_platform_specific_data(client):
    """Создает специфичные данные для каждой платформы"""
    
    # Telegram данные
    telegram_data = []
    for i in range(50):
        date = datetime.now() - timedelta(days=random.randint(0, 7))
        telegram_data.append([
            i + 1,
            f'test_channel_{i}',
            f'test_user_{i}',
            f'Telegram пост #{i}',
            date,
            random.randint(10, 1000),  # views
            random.randint(0, 50),     # forwards
            round(random.uniform(0, 100), 1),  # extremism_percentage
            random.choice(['low', 'medium', 'high', 'critical']),
            random.randint(1, 5)
        ])
    
    client.execute("""
        INSERT INTO social_media.telegram_posts 
        (id, channel_name, author_name, text, created_at, views, forwards, extremism_percentage, risk_level, keywords_matched)
        VALUES
    """, telegram_data)
    
    # Twitter данные
    twitter_data = []
    for i in range(50):
        date = datetime.now() - timedelta(days=random.randint(0, 7))
        twitter_data.append([
            i + 1,
            f'test_user_{i}',
            f'Twitter пост #{i}',
            date,
            random.randint(0, 100),    # retweets
            random.randint(0, 200),    # likes
            round(random.uniform(0, 100), 1),  # extremism_percentage
            random.choice(['low', 'medium', 'high', 'critical']),
            random.randint(1, 5)
        ])
    
    client.execute("""
        INSERT INTO social_media.twitter_posts 
        (id, author_name, text, created_at, retweets, likes, extremism_percentage, risk_level, keywords_matched)
        VALUES
    """, twitter_data)
    
    # VK данные
    vk_data = []
    for i in range(50):
        date = datetime.now() - timedelta(days=random.randint(0, 7))
        vk_data.append([
            i + 1,
            f'test_user_{i}',
            f'VK пост #{i}',
            date,
            random.randint(0, 50),     # likes
            random.randint(0, 20),     # reposts
            round(random.uniform(0, 100), 1),  # extremism_percentage
            random.choice(['low', 'medium', 'high', 'critical']),
            random.randint(1, 5)
        ])
    
    client.execute("""
        INSERT INTO social_media.vk_posts 
        (id, author_name, text, created_at, likes, reposts, extremism_percentage, risk_level, keywords_matched)
        VALUES
    """, vk_data)

def create_analytics_summary(client):
    """Создает сводные аналитические данные"""
    print("📊 Создание аналитических сводок...")
    
    # Создаем таблицу для аналитических сводок если не существует
    try:
        client.execute("""
            CREATE TABLE IF NOT EXISTS analytics.daily_summary (
                date Date,
                total_news Int32,
                total_social_posts Int32,
                avg_sentiment Float32,
                high_risk_posts Int32,
                top_category String,
                tension_level String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY date
        """)
    except:
        pass
    
    # Генерируем ежедневные сводки за последние 30 дней
    summary_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(30):
        date = (base_date + timedelta(days=i)).date()
        
        # Генерируем реалистичные показатели
        total_news = random.randint(10, 50)
        total_social_posts = random.randint(20, 100)
        avg_sentiment = round(random.uniform(-0.5, 0.5), 3)
        high_risk_posts = random.randint(0, 10)
        top_category = random.choice(['military', 'diplomatic', 'economic', 'humanitarian', 'information'])
        
        # Определяем уровень напряженности
        if high_risk_posts <= 2:
            tension_level = 'low'
        elif high_risk_posts <= 5:
            tension_level = 'medium'
        elif high_risk_posts <= 8:
            tension_level = 'high'
        else:
            tension_level = 'critical'
        
        summary_data.append([
            date,
            total_news,
            total_social_posts,
            avg_sentiment,
            high_risk_posts,
            top_category,
            tension_level,
            datetime.now()
        ])
    
    # Очищаем старые данные и вставляем новые
    try:
        client.execute("DELETE FROM analytics.daily_summary WHERE date >= today() - 30")
        client.execute("""
            INSERT INTO analytics.daily_summary 
            (date, total_news, total_social_posts, avg_sentiment, high_risk_posts, top_category, tension_level, created_at)
            VALUES
        """, summary_data)
        print(f"✅ Создано {len(summary_data)} ежедневных сводок")
    except Exception as e:
        print(f"⚠️ Ошибка при создании аналитических сводок: {e}")

if __name__ == "__main__":
    create_comprehensive_analytics()