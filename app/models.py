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


class SocialMediaData:
    """Класс для работы с данными социальных сетей."""
    
    def __init__(self):
        self.client = get_clickhouse_client()
    
    def get_all_social_posts(self, platform='all', limit=100, days=7):
        """Получение постов из всех социальных сетей."""
        if platform == 'all':
            query = """
                SELECT id, platform, author_name, text, created_at, 
                       extremism_percentage, risk_level, keywords_matched
                FROM social_media.all_posts 
                WHERE created_at >= today() - {days}
                ORDER BY created_at DESC 
                LIMIT {limit}
            """.format(days=days, limit=limit)
        else:
            query = """
                SELECT id, platform, author_name, text, created_at, 
                       extremism_percentage, risk_level, keywords_matched
                FROM social_media.all_posts 
                WHERE platform = '{platform}' AND created_at >= today() - {days}
                ORDER BY created_at DESC 
                LIMIT {limit}
            """.format(platform=platform, days=days, limit=limit)
        
        return self.client.query(query).result_rows
    
    def get_twitter_posts(self, limit=100, days=7):
        """Получение постов из Twitter."""
        query = """
            SELECT id, text, author_username, author_name, created_at,
                   public_metrics_like_count, public_metrics_retweet_count,
                   extremism_percentage, risk_level, hashtags, keywords_matched
            FROM social_media.twitter_posts 
            WHERE created_at >= today() - {days}
            ORDER BY created_at DESC 
            LIMIT {limit}
        """.format(days=days, limit=limit)
        
        return self.client.query(query).result_rows
    
    def get_vk_posts(self, limit=100, days=7):
        """Получение постов из VKontakte."""
        query = """
            SELECT id, text, from_id, date, likes_count, reposts_count,
                   extremism_percentage, risk_level, keywords_matched
            FROM social_media.vk_posts 
            WHERE date >= today() - {days}
            ORDER BY date DESC 
            LIMIT {limit}
        """.format(days=days, limit=limit)
        
        return self.client.query(query).result_rows
    
    def get_ok_posts(self, limit=100, days=7):
        """Получение постов из Одноклассники."""
        query = """
            SELECT id, text, author_name, created_time, likes_count,
                   extremism_percentage, risk_level, keywords_matched
            FROM social_media.ok_posts 
            WHERE created_time >= today() - {days}
            ORDER BY created_time DESC 
            LIMIT {limit}
        """.format(days=days, limit=limit)
        
        return self.client.query(query).result_rows
    
    def get_social_stats(self, platform='all', days=7):
        """Получение статистики по социальным сетям."""
        if platform == 'all':
            query = """
                SELECT platform, count() as total_posts,
                       countIf(extremism_percentage > 50) as extremist_posts,
                       avg(extremism_percentage) as avg_extremism
                FROM social_media.all_posts 
                WHERE created_at >= today() - {days}
                GROUP BY platform
                ORDER BY total_posts DESC
            """.format(days=days)
        else:
            query = """
                SELECT platform, count() as total_posts,
                       countIf(extremism_percentage > 50) as extremist_posts,
                       avg(extremism_percentage) as avg_extremism
                FROM social_media.all_posts 
                WHERE platform = '{platform}' AND created_at >= today() - {days}
                GROUP BY platform
            """.format(platform=platform, days=days)
        
        return self.client.query(query).result_rows
    
    def get_parsing_stats(self, platform='all', days=7):
        """Получение статистики парсинга."""
        if platform == 'all':
            query = """
                SELECT platform, start_time, end_time, total_posts, 
                       extremist_posts, status
                FROM social_media.parsing_stats 
                WHERE start_time >= today() - {days}
                ORDER BY start_time DESC
            """.format(days=days)
        else:
            query = """
                SELECT platform, start_time, end_time, total_posts, 
                       extremist_posts, status
                FROM social_media.parsing_stats 
                WHERE platform = '{platform}' AND start_time >= today() - {days}
                ORDER BY start_time DESC
            """.format(platform=platform, days=days)
        
        return self.client.query(query).result_rows
    
    def search_social_posts(self, search_term, platform='all', limit=100):
        """Поиск постов в социальных сетях."""
        if platform == 'all':
            query = """
                SELECT id, platform, author_name, text, created_at, 
                       extremism_percentage, risk_level
                FROM social_media.all_posts 
                WHERE text ILIKE '%{search_term}%'
                ORDER BY created_at DESC 
                LIMIT {limit}
            """.format(search_term=search_term, limit=limit)
        else:
            query = """
                SELECT id, platform, author_name, text, created_at, 
                       extremism_percentage, risk_level
                FROM social_media.all_posts 
                WHERE text ILIKE '%{search_term}%' AND platform = '{platform}'
                ORDER BY created_at DESC 
                LIMIT {limit}
            """.format(search_term=search_term, platform=platform, limit=limit)
        
        return self.client.query(query).result_rows
    
    def insert_twitter_post(self, post_data):
        """Добавление поста Twitter в базу данных."""
        query = """
            INSERT INTO social_media.twitter_posts 
            (id, text, author_id, author_username, author_name, created_at,
             public_metrics_retweet_count, public_metrics_like_count,
             public_metrics_reply_count, public_metrics_quote_count,
             lang, hashtags, mentions, urls, extremism_percentage, 
             risk_level, analysis_method, keywords_matched)
            VALUES
        """
        self.client.insert('social_media.twitter_posts', [post_data])
    
    def insert_vk_post(self, post_data):
        """Добавление поста VK в базу данных."""
        self.client.insert('social_media.vk_posts', [post_data])
    
    def insert_ok_post(self, post_data):
        """Добавление поста OK в базу данных."""
        self.client.insert('social_media.ok_posts', [post_data])
    
    def insert_parsing_stat(self, stat_data):
        """Добавление статистики парсинга."""
        self.client.insert('social_media.parsing_stats', [stat_data])
    
    def get_available_platforms(self):
        """Получение списка доступных платформ."""
        return ['twitter', 'vk', 'ok', 'telegram']
    
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