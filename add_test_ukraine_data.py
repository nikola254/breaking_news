#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления тестовых данных в таблицы ukraine_conflict
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clickhouse_driver import Client
from config import Config
import logging
from datetime import datetime, timedelta
import random
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Тестовые данные для украинского конфликта
TEST_NEWS_DATA = [
    {
        'title': 'Военные операции в восточных регионах продолжаются',
        'content': 'Сводка военных действий за последние сутки. Обстановка остается напряженной.',
        'source': 'РИА Новости',
        'category': 'military_operations',
        'relevance_score': 0.95,
        'keywords_found': ['военные', 'операции', 'восточные регионы'],
        'sentiment_score': -0.7,
        'impact_level': 'high'
    },
    {
        'title': 'Гуманитарная помощь доставлена в пострадавшие районы',
        'content': 'Международные организации продолжают оказывать помощь мирному населению.',
        'source': 'ТАСС',
        'category': 'humanitarian_crisis',
        'relevance_score': 0.88,
        'keywords_found': ['гуманитарная помощь', 'пострадавшие районы'],
        'sentiment_score': 0.3,
        'impact_level': 'medium'
    },
    {
        'title': 'Экономические санкции влияют на мировые рынки',
        'content': 'Анализ влияния санкций на глобальную экономику и торговые отношения.',
        'source': 'Коммерсант',
        'category': 'economic_consequences',
        'relevance_score': 0.82,
        'keywords_found': ['санкции', 'мировые рынки', 'экономика'],
        'sentiment_score': -0.5,
        'impact_level': 'high'
    },
    {
        'title': 'Переговоры между сторонами конфликта',
        'content': 'Дипломатические усилия по урегулированию ситуации продолжаются.',
        'source': 'Интерфакс',
        'category': 'political_decisions',
        'relevance_score': 0.91,
        'keywords_found': ['переговоры', 'дипломатия', 'урегулирование'],
        'sentiment_score': 0.4,
        'impact_level': 'medium'
    },
    {
        'title': 'Информационная война в социальных сетях',
        'content': 'Анализ распространения информации и дезинформации в интернете.',
        'source': 'Медуза',
        'category': 'information_social',
        'relevance_score': 0.76,
        'keywords_found': ['информационная война', 'социальные сети'],
        'sentiment_score': -0.3,
        'impact_level': 'medium'
    },
    {
        'title': 'Беженцы получают поддержку в соседних странах',
        'content': 'Статистика по размещению и поддержке беженцев в европейских странах.',
        'source': 'BBC',
        'category': 'humanitarian_crisis',
        'relevance_score': 0.85,
        'keywords_found': ['беженцы', 'поддержка', 'европейские страны'],
        'sentiment_score': 0.2,
        'impact_level': 'medium'
    },
    {
        'title': 'Энергетический кризис в Европе',
        'content': 'Влияние конфликта на поставки энергоресурсов и цены на газ.',
        'source': 'Газета.ру',
        'category': 'economic_consequences',
        'relevance_score': 0.89,
        'keywords_found': ['энергетический кризис', 'газ', 'поставки'],
        'sentiment_score': -0.6,
        'impact_level': 'high'
    },
    {
        'title': 'Международная поддержка украинской стороны',
        'content': 'Обзор военной и финансовой помощи от союзников.',
        'source': 'Лента.ру',
        'category': 'political_decisions',
        'relevance_score': 0.87,
        'keywords_found': ['международная поддержка', 'военная помощь'],
        'sentiment_score': 0.5,
        'impact_level': 'high'
    },
    {
        'title': 'Пропаганда и контрпропаганда в СМИ',
        'content': 'Анализ информационных кампаний различных сторон конфликта.',
        'source': 'РБК',
        'category': 'information_social',
        'relevance_score': 0.73,
        'keywords_found': ['пропаганда', 'СМИ', 'информационные кампании'],
        'sentiment_score': -0.4,
        'impact_level': 'medium'
    },
    {
        'title': 'Восстановление разрушенной инфраструктуры',
        'content': 'Планы по восстановлению городов и инфраструктуры после конфликта.',
        'source': 'Ведомости',
        'category': 'economic_consequences',
        'relevance_score': 0.81,
        'keywords_found': ['восстановление', 'инфраструктура'],
        'sentiment_score': 0.3,
        'impact_level': 'medium'
    }
]

def add_test_data():
    """Добавление тестовых данных в таблицу ukraine_conflict.all_news"""
    
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    try:
        # Подготавливаем данные для вставки
        insert_data = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i, news_item in enumerate(TEST_NEWS_DATA):
            # Генерируем разные даты для новостей
            published_date = base_date + timedelta(days=random.randint(0, 30), 
                                                 hours=random.randint(0, 23))
            
            data_row = {
                'id': str(uuid.uuid4()),
                'site_name': news_item['source'],
                'url': f'https://example.com/news/{i+1}',
                'title': news_item['title'],
                'content': news_item['content'],
                'category': news_item['category'],
                'relevance_score': news_item['relevance_score'],
                'ai_confidence': 0.85,
                'keywords_found': news_item['keywords_found'],
                'sentiment_score': news_item['sentiment_score'],
                'published_date': published_date,
                'published_date': datetime.now(),
                'language': 'ru',
                'tags': [news_item['category'], 'ukraine'],
                'metadata': f'{{"impact_level": "{news_item["impact_level"]}"}}'
            }
            insert_data.append(data_row)
        
        # Вставляем данные в основную таблицу
        client.execute(
            'INSERT INTO news.ukraine_universal_news VALUES',
            insert_data
        )
        
        logger.info(f"Добавлено {len(insert_data)} тестовых записей в news.ukraine_universal_news")
        
        # Проверяем количество записей
        result = client.execute('SELECT COUNT(*) FROM news.ukraine_universal_news')
        logger.info(f"Общее количество записей в таблице: {result[0][0]}")
        
        # Показываем статистику по категориям
        category_stats = client.execute('''
            SELECT category, COUNT(*) as count, AVG(sentiment_score) as avg_sentiment
            FROM news.ukraine_universal_news 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        
        logger.info("\n=== Статистика по категориям ===")
        for category, count, avg_sentiment in category_stats:
            logger.info(f"{category}: {count} записей, средний sentiment: {avg_sentiment:.2f}")
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении тестовых данных: {e}")
        raise

if __name__ == "__main__":
    logger.info("Начинаем добавление тестовых данных...")
    add_test_data()
    logger.info("Тестовые данные добавлены успешно!")
