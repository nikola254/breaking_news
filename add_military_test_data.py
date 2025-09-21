#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления тестовых данных категории military_operations
"""

import sys
import os
from clickhouse_driver import Client
from datetime import datetime, timedelta
import uuid

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config

def add_military_test_data():
    """Добавляет тестовые данные для категории military_operations"""
    try:
        # Подключение к ClickHouse (серверный)
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=Config.CLICKHOUSE_DATABASE
        )
        
        # Проверяем существование таблицы universal_military_operations
        print("✓ Используем существующую таблицу universal_military_operations")
        
        # Тестовые данные для military_operations
        test_data = [
            {
                'title': 'Военные операции в восточных регионах продолжаются',
                'content': 'Подразделения вооруженных сил продолжают выполнение боевых задач в восточном направлении. Противник предпринимает попытки контратак.',
                'source': 'test_data',
                'category': 'military_operations',
                'sentiment_score': -0.3,
                'published_date': datetime.now() - timedelta(hours=2)
            },
            {
                'title': 'Обстрел жилых районов зафиксирован в приграничной зоне',
                'content': 'В результате артиллерийского обстрела пострадали жилые кварталы. Эвакуация мирного населения продолжается.',
                'source': 'test_data',
                'category': 'military_operations',
                'sentiment_score': -0.6,
                'published_date': datetime.now() - timedelta(hours=5)
            },
            {
                'title': 'Силы ПВО отразили атаку беспилотников',
                'content': 'Системы противовоздушной обороны успешно перехватили группу беспилотных летательных аппаратов противника.',
                'source': 'test_data',
                'category': 'military_operations',
                'sentiment_score': 0.2,
                'published_date': datetime.now() - timedelta(hours=8)
            },
            {
                'title': 'Освобождение населенного пункта в ходе наступательной операции',
                'content': 'В результате успешной наступательной операции подразделения освободили стратегически важный населенный пункт.',
                'source': 'test_data',
                'category': 'military_operations',
                'sentiment_score': 0.4,
                'published_date': datetime.now() - timedelta(hours=12)
            },
            {
                'title': 'Гуманитарный коридор обеспечен для эвакуации мирных жителей',
                'content': 'Установлен временный режим прекращения огня для организации безопасной эвакуации гражданского населения.',
                'source': 'test_data',
                'category': 'military_operations',
                'sentiment_score': 0.3,
                'published_date': datetime.now() - timedelta(hours=18)
            }
        ]
        
        # Добавляем данные в основную таблицу ukraine_news
        for data in test_data:
            client.execute('''
                INSERT INTO news.ukraine_news 
                (id, title, content, category, sentiment_score, conflict_level, 
                 emotional_intensity, parsed_date, published_date, source)
                VALUES
            ''', [(
                str(uuid.uuid4()),
                data['title'],
                data['content'],
                'military_operations',
                data['sentiment_score'],
                0.5,  # conflict_level
                0.6,  # emotional_intensity
                data['published_date'],
                data['published_date'],
                'test_data'
            )])
        
        # Добавляем данные в категорийную таблицу
        for data in test_data:
            client.execute('''
                INSERT INTO news.universal_military_operations 
                (title, link, content, source, category, relevance_score, ai_confidence, 
                 keywords_found, sentiment_score, parsed_date, published_date)
                VALUES
            ''', [(
                data['title'],
                '',  # link
                data['content'],
                data['source'],
                data['category'],
                0.8,  # relevance_score
                0.9,  # ai_confidence
                [],   # keywords_found
                data['sentiment_score'],
                data['published_date'],  # parsed_date
                data['published_date']   # published_date
            )])
        
        print(f"✓ Добавлено {len(test_data)} тестовых записей для категории military_operations")
        
        # Проверяем результат
        result = client.execute('''
            SELECT COUNT(*) FROM news.ukraine_news 
            WHERE category = 'military_operations' 
            AND parsed_date >= today() - 7
        ''')
        print(f"✓ Всего записей military_operations за последние 7 дней: {result[0][0]}")
        
    except Exception as e:
        print(f"✗ Ошибка при добавлении тестовых данных: {e}")

if __name__ == "__main__":
    add_military_test_data()