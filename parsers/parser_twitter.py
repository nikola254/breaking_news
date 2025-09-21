"""Парсер новостей из Twitter.

Этот модуль содержит:
- Подключение к Twitter API v2
- Парсинг твитов из указанных аккаунтов
- Сохранение новостей в ClickHouse
- Автоматическую категоризацию новостей
- Фильтрацию по релевантности к украинскому конфликту
"""

import requests
import json
import time
import os
import sys
from datetime import datetime, timedelta
from clickhouse_driver import Client as ClickHouseClient
from dotenv import load_dotenv
import logging

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Load environment variables from .env file
load_dotenv()

# Twitter API credentials
BEARER_TOKEN = Config.TWITTER_BEARER_TOKEN

# Список Twitter аккаунтов для парсинга (новостные и аналитические)
TWITTER_ACCOUNTS = [
    'BBCBreaking',
    'Reuters',
    'AP',
    'CNN',
    'nytimes',
    'washingtonpost',
    'guardian',
    'dwnews',
    'euronews',
    'France24_en',
    'AlJazeera',
    'RT_com',
    'KyivIndependent',
    'ZelenskyyUa',
    'DefenceU',
    'MFA_Ukraine'
]

# Ключевые слова для фильтрации украинских новостей
UKRAINE_KEYWORDS = [
    'ukraine', 'ukrainian', 'kyiv', 'kiev', 'zelensky', 'putin', 'russia', 'russian',
    'donbas', 'crimea', 'mariupol', 'kharkiv', 'odesa', 'lviv', 'dnipro',
    'war', 'conflict', 'invasion', 'military', 'nato', 'eu', 'sanctions',
    'украина', 'украинский', 'киев', 'зеленский', 'путин', 'россия', 'российский',
    'донбасс', 'крым', 'мариуполь', 'харьков', 'одесса', 'львов', 'днепр',
    'война', 'конфликт', 'вторжение', 'военный', 'нато', 'ес', 'санкции'
]

def create_ukraine_tables_if_not_exists():
    """Создание таблицы в ClickHouse для хранения Twitter новостей."""
    client = ClickHouseClient(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )
    
    # Создаем базу данных если не существует
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Создаем таблицу для Twitter новостей
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS news.twitter_headlines (
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
    ORDER BY date
    '''
    
    client.execute(create_table_query)
    logging.info("Twitter таблица создана или уже существует")

class TwitterParser:
    """Класс для парсинга новостей из Twitter"""
    
    def __init__(self):
        self.bearer_token = BEARER_TOKEN
        self.base_url = "https://api.twitter.com/2"
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        
        # Инициализация ClickHouse клиента
        self.clickhouse_client = ClickHouseClient(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=Config.CLICKHOUSE_DATABASE
        )
        
    def _make_request(self, endpoint: str, params: dict = None):
        """Выполнение запроса к Twitter API v2"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 429:  # Rate limit
                self.logger.warning("Rate limit reached, waiting...")
                time.sleep(900)  # Ждем 15 минут
                return self._make_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            self.logger.error(f"Twitter API request error: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None
    
    def get_user_id(self, username: str):
        """Получение ID пользователя по username"""
        response = self._make_request(f"users/by/username/{username}")
        if response and 'data' in response:
            return response['data']['id']
        return None
    
    def get_user_tweets(self, user_id: str, max_results: int = 100):
        """Получение твитов пользователя"""
        params = {
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,author_id,public_metrics,context_annotations,lang,possibly_sensitive',
            'exclude': 'retweets,replies'
        }
        
        response = self._make_request(f"users/{user_id}/tweets", params)
        return response.get('data', []) if response else []
    
    def is_ukraine_related(self, text: str):
        """Проверка релевантности твита к украинскому конфликту"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in UKRAINE_KEYWORDS)
    
    def categorize_news(self, text: str):
        """Простая категоризация новостей"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['military', 'army', 'weapon', 'attack', 'battle', 'военный', 'армия', 'оружие', 'атака', 'бой']):
            return 'military_operations'
        elif any(word in text_lower for word in ['diplomatic', 'negotiation', 'peace', 'talk', 'дипломатический', 'переговоры', 'мир', 'переговоры']):
            return 'diplomatic_efforts'
        elif any(word in text_lower for word in ['economic', 'sanction', 'trade', 'oil', 'gas', 'экономический', 'санкции', 'торговля', 'нефть', 'газ']):
            return 'economic_consequences'
        elif any(word in text_lower for word in ['humanitarian', 'refugee', 'civilian', 'aid', 'гуманитарный', 'беженец', 'гражданский', 'помощь']):
            return 'humanitarian_crisis'
        elif any(word in text_lower for word in ['political', 'government', 'president', 'minister', 'политический', 'правительство', 'президент', 'министр']):
            return 'political_decisions'
        else:
            return 'information_social'
    
    def calculate_metrics(self, text: str):
        """Расчет метрик для новости"""
        # Простые эвристики для расчета метрик
        text_lower = text.lower()
        
        # Sentiment score (-1 to 1)
        negative_words = ['war', 'death', 'destroy', 'attack', 'kill', 'bomb', 'война', 'смерть', 'разрушение', 'атака', 'убить', 'бомба']
        positive_words = ['peace', 'help', 'aid', 'support', 'victory', 'мир', 'помощь', 'поддержка', 'победа']
        
        neg_count = sum(1 for word in negative_words if word in text_lower)
        pos_count = sum(1 for word in positive_words if word in text_lower)
        
        sentiment_score = (pos_count - neg_count) / max(len(text.split()), 1)
        sentiment_score = max(-1, min(1, sentiment_score))
        
        # Tension score (0 to 100)
        tension_words = ['crisis', 'urgent', 'breaking', 'emergency', 'critical', 'кризис', 'срочно', 'экстренный', 'критический']
        tension_count = sum(1 for word in tension_words if word in text_lower)
        tension_score = min(100, tension_count * 20)
        
        # Conflict level (0 to 1)
        conflict_words = ['fight', 'battle', 'combat', 'strike', 'бой', 'битва', 'удар', 'сражение']
        conflict_count = sum(1 for word in conflict_words if word in text_lower)
        conflict_level = min(1, conflict_count * 0.3)
        
        # Urgency factor (0 to 1)
        urgency_words = ['now', 'immediate', 'urgent', 'breaking', 'сейчас', 'немедленно', 'срочно']
        urgency_count = sum(1 for word in urgency_words if word in text_lower)
        urgency_factor = min(1, urgency_count * 0.4)
        
        # Emotional intensity (0 to 1)
        emotional_words = ['shocking', 'terrible', 'amazing', 'incredible', 'шокирующий', 'ужасный', 'удивительный', 'невероятный']
        emotional_count = sum(1 for word in emotional_words if word in text_lower)
        emotional_intensity = min(1, emotional_count * 0.3)
        
        # Tension category
        if tension_score >= 70:
            tension_category = 'high'
        elif tension_score >= 30:
            tension_category = 'medium'
        elif tension_score >= 10:
            tension_category = 'low'
        else:
            tension_category = 'minimal'
        
        return {
            'sentiment_score': sentiment_score,
            'tension_score': tension_score,
            'conflict_level': conflict_level,
            'urgency_factor': urgency_factor,
            'emotional_intensity': emotional_intensity,
            'tension_category': tension_category
        }
    
    def save_to_clickhouse(self, tweets_data):
        """Сохранение данных в ClickHouse"""
        if not tweets_data:
            return
        
        try:
            self.clickhouse_client.execute(
                'INSERT INTO news.twitter_headlines VALUES',
                tweets_data
            )
            self.logger.info(f"Сохранено {len(tweets_data)} твитов в ClickHouse")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения в ClickHouse: {e}")
    
    def parse_tweets(self, hours_back: int = 24):
        """Основной метод парсинга твитов"""
        if not self.bearer_token:
            self.logger.warning("Twitter Bearer Token не настроен, используем тестовые данные")
            self._parse_test_data()
            return
        
        self.logger.info("Начинаем парсинг Twitter...")
        
        all_tweets_data = []
        
        for username in TWITTER_ACCOUNTS:
            try:
                self.logger.info(f"Парсинг аккаунта @{username}")
                
                # Получаем ID пользователя
                user_id = self.get_user_id(username)
                if not user_id:
                    self.logger.warning(f"Не удалось получить ID для @{username}")
                    continue
                
                # Получаем твиты
                tweets = self.get_user_tweets(user_id, max_results=50)
                
                for tweet in tweets:
                    # Проверяем релевантность к украинскому конфликту
                    if not self.is_ukraine_related(tweet['text']):
                        continue
                    
                    # Проверяем дату (только последние часы)
                    tweet_date = datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00'))
                    if tweet_date < datetime.now().replace(tzinfo=tweet_date.tzinfo) - timedelta(hours=hours_back):
                        continue
                    
                    # Категоризация и расчет метрик
                    category = self.categorize_news(tweet['text'])
                    metrics = self.calculate_metrics(tweet['text'])
                    
                    # Формируем URL твита
                    tweet_url = f"https://twitter.com/{username}/status/{tweet['id']}"
                    
                    # Подготавливаем данные для сохранения
                    tweet_data = (
                        tweet['id'],
                        tweet['text'][:200],  # Заголовок - первые 200 символов
                        tweet['text'],
                        tweet_url,
                        f"twitter_{username}",
                        username,
                        tweet_date.replace(tzinfo=None),  # Убираем timezone для ClickHouse
                        category,
                        metrics['sentiment_score'],
                        metrics['tension_score'],
                        metrics['conflict_level'],
                        metrics['urgency_factor'],
                        metrics['emotional_intensity'],
                        metrics['tension_category'],
                        datetime.now()  # created_at
                    )
                    
                    all_tweets_data.append(tweet_data)
                
                # Небольшая пауза между запросами
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Ошибка при парсинге @{username}: {e}")
                continue
        
        # Сохраняем все данные
        if all_tweets_data:
            self.save_to_clickhouse(all_tweets_data)
            self.logger.info(f"Парсинг завершен. Обработано {len(all_tweets_data)} релевантных твитов")
        else:
            self.logger.info("Релевантных твитов не найдено")
    
    def _parse_test_data(self):
        """Генерация тестовых данных для демонстрации работы парсера"""
        self.logger.info("Генерируем тестовые данные Twitter...")
        
        test_tweets = [
            {
                'id': 'test_twitter_1',
                'text': 'Breaking: Ukraine reports successful defense operation in eastern region. Military officials confirm strategic positions maintained.',
                'username': 'BBCBreaking',
                'category': 'military_operations'
            },
            {
                'id': 'test_twitter_2', 
                'text': 'EU announces new sanctions package targeting Russian energy sector. Economic pressure continues to mount.',
                'username': 'Reuters',
                'category': 'economic_consequences'
            },
            {
                'id': 'test_twitter_3',
                'text': 'Humanitarian aid convoy reaches besieged city. International organizations coordinate relief efforts for civilians.',
                'username': 'UN_News',
                'category': 'humanitarian_crisis'
            },
            {
                'id': 'test_twitter_4',
                'text': 'Diplomatic talks scheduled for next week. Peace negotiations remain priority despite ongoing tensions.',
                'username': 'DiplomaticNews',
                'category': 'diplomatic_efforts'
            },
            {
                'id': 'test_twitter_5',
                'text': 'Information warfare intensifies on social media platforms. Experts warn of increased disinformation campaigns.',
                'username': 'CyberSecNews',
                'category': 'information_social'
            }
        ]
        
        all_tweets_data = []
        current_time = datetime.now()
        
        for i, tweet_data in enumerate(test_tweets):
            # Рассчитываем метрики
            metrics = self.calculate_metrics(tweet_data['text'])
            
            # Создаем временную метку (последние 24 часа)
            tweet_time = current_time - timedelta(hours=i*4)
            
            # Формируем URL
            tweet_url = f"https://twitter.com/{tweet_data['username']}/status/{tweet_data['id']}"
            
            # Подготавливаем данные для сохранения
            tweet_record = (
                tweet_data['id'],
                tweet_data['text'][:200],  # Заголовок
                tweet_data['text'],        # Полный текст
                tweet_url,
                f"twitter_{tweet_data['username']}",
                tweet_data['username'],
                tweet_time,
                tweet_data['category'],
                metrics['sentiment_score'],
                metrics['tension_score'],
                metrics['conflict_level'],
                metrics['urgency_factor'],
                metrics['emotional_intensity'],
                metrics['tension_category'],
                current_time  # created_at
            )
            
            all_tweets_data.append(tweet_record)
        
        # Сохраняем тестовые данные
        if all_tweets_data:
            self.save_to_clickhouse(all_tweets_data)
            self.logger.info(f"Сохранено {len(all_tweets_data)} тестовых твитов")

def main():
    """Основная функция для запуска парсера"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаем таблицы если не существуют
    create_ukraine_tables_if_not_exists()
    
    # Запускаем парсер
    parser = TwitterParser()
    parser.parse_tweets(hours_back=24)

if __name__ == "__main__":
    main()