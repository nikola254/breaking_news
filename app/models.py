"""Модели данных и подключение к базе данных ClickHouse.

Этот модуль содержит:
- Конфигурацию подключения к ClickHouse
- Функции для создания клиентов базы данных
- Общие модели данных для работы с новостями
- Модели для анализа социальных сетей
"""

import clickhouse_connect
from config import Config

# Модели социальных сетей будут импортированы из отдельного модуля
# from app.models.social_models import *

# Получаем настройки из конфигурации
CLICKHOUSE_HOST = Config.CLICKHOUSE_HOST
# Используем HTTP порт для clickhouse_connect, а не нативный порт
CLICKHOUSE_PORT = Config.CLICKHOUSE_PORT  # HTTP порт 8123
CLICKHOUSE_USER = Config.CLICKHOUSE_USER
CLICKHOUSE_PASSWORD = Config.CLICKHOUSE_PASSWORD

def get_clickhouse_client():
    """Создание HTTP клиента для подключения к ClickHouse.
    
    Использует clickhouse_connect для HTTP подключения к ClickHouse.
    Это предпочтительный способ для веб-приложений.
    
    Returns:
        clickhouse_connect.Client: HTTP клиент ClickHouse
    """
    # Если пароль пустой, не передаем его в параметрах
    if CLICKHOUSE_PASSWORD:
        return clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,  # Используем HTTP порт 8123
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD
        )
    else:
        return clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,  # Используем HTTP порт 8123
            username=CLICKHOUSE_USER
        )

class UkraineConflictNews:
    """Модель для работы с новостями украинского конфликта."""
    
    def __init__(self):
        self.client = get_clickhouse_client()
    
    def get_all_news(self, category='all', limit=100, offset=0):
        """Получение всех новостей из таблицы ukraine_conflict.all_news."""
        if category == 'all':
            query = """
                SELECT id, title, content, source, category, relevance_score, 
                       ai_confidence, sentiment_score, parsed_date, published_date
                FROM ukraine_conflict.all_news 
                ORDER BY parsed_date DESC 
                LIMIT {limit} OFFSET {offset}
            """.format(limit=limit, offset=offset)
        else:
            query = """
                SELECT id, title, content, source, category, relevance_score, 
                       ai_confidence, sentiment_score, parsed_date, published_date
                FROM ukraine_conflict.all_news 
                WHERE category = '{category}'
                ORDER BY parsed_date DESC 
                LIMIT {limit} OFFSET {offset}
            """.format(category=category, limit=limit, offset=offset)
        
        return self.client.query(query).result_rows
    
    def get_category_news(self, category, limit=100, offset=0):
        """Получение новостей из конкретной категории."""
        table_name = f"ukraine_conflict.{category}"
        query = """
            SELECT id, title, content, source, relevance_score, 
                   ai_confidence, sentiment_score, parsed_date, published_date
            FROM {table_name} 
            ORDER BY parsed_date DESC 
            LIMIT {limit} OFFSET {offset}
        """.format(table_name=table_name, limit=limit, offset=offset)
        
        return self.client.query(query).result_rows
    
    def get_daily_analytics(self, category='all', days=7):
        """Получение ежедневной аналитики."""
        if category == 'all':
            query = """
                SELECT date, total_news, avg_sentiment, avg_relevance, 
                       tension_level, top_keywords
                FROM ukraine_conflict.daily_analytics 
                WHERE date >= today() - {days}
                ORDER BY date DESC
            """.format(days=days)
        else:
            query = """
                SELECT date, total_news, avg_sentiment, avg_relevance, 
                       tension_level, top_keywords
                FROM ukraine_conflict.daily_analytics 
                WHERE category = '{category}' AND date >= today() - {days}
                ORDER BY date DESC
            """.format(category=category, days=days)
        
        return self.client.query(query).result_rows
    
    def get_social_tension_metrics(self, category='all', days=7):
        """Получение метрик социальной напряженности."""
        if category == 'all':
            query = """
                SELECT date, hour, tension_score, news_volume, 
                       sentiment_volatility, keyword_intensity
                FROM ukraine_conflict.social_tension_metrics 
                WHERE date >= today() - {days}
                ORDER BY date DESC, hour DESC
            """.format(days=days)
        else:
            query = """
                SELECT date, hour, tension_score, news_volume, 
                       sentiment_volatility, keyword_intensity
                FROM ukraine_conflict.social_tension_metrics 
                WHERE category = '{category}' AND date >= today() - {days}
                ORDER BY date DESC, hour DESC
            """.format(category=category, days=days)
        
        return self.client.query(query).result_rows
    
    def get_available_categories(self):
        """Получение списка доступных категорий."""
        return [
            'military_operations',
            'humanitarian_crisis', 
            'economic_consequences',
            'political_decisions',
            'information_social'
        ]
    
    def get_news_count(self, category='all'):
        """Получение количества новостей в категории."""
        if category == 'all':
            query = "SELECT count() FROM ukraine_conflict.all_news"
        else:
            query = f"SELECT count() FROM ukraine_conflict.{category}"
        
        result = self.client.query(query).result_rows
        return result[0][0] if result else 0
    
    def search_news(self, search_term, category='all', limit=100):
        """Поиск новостей по ключевому слову."""
        if category == 'all':
            query = """
                SELECT id, title, content, source, category, relevance_score, 
                       ai_confidence, sentiment_score, parsed_date, published_date
                FROM ukraine_conflict.all_news 
                WHERE title ILIKE '%{search_term}%' OR content ILIKE '%{search_term}%'
                ORDER BY parsed_date DESC 
                LIMIT {limit}
            """.format(search_term=search_term, limit=limit)
        else:
            query = """
                SELECT id, title, content, source, category, relevance_score, 
                       ai_confidence, sentiment_score, parsed_date, published_date
                FROM ukraine_conflict.all_news 
                WHERE (title ILIKE '%{search_term}%' OR content ILIKE '%{search_term}%') 
                      AND category = '{category}'
                ORDER BY parsed_date DESC 
                LIMIT {limit}
            """.format(search_term=search_term, category=category, limit=limit)
        
        return self.client.query(query).result_rows