"""
Базовый класс для всех парсеров новостей
Включает предобработку, классификацию и проверку дубликатов
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# Добавляем путь к корневой директории
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clickhouse_driver import Client
from config import Config
from parsers.news_preprocessor import preprocessor
from parsers.improved_classifier import classifier
from parsers.duplicate_checker import create_duplicate_checker

# Импортируем анализатор тональности
try:
    from app.utils.ukraine_sentiment_analyzer import get_ukraine_sentiment_analyzer
    SENTIMENT_ANALYZER_AVAILABLE = True
except ImportError:
    SENTIMENT_ANALYZER_AVAILABLE = False
    print("Warning: UkraineSentimentAnalyzer not available")


def get_clickhouse_client():
    """Получение клиента ClickHouse"""
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )


class BaseNewsParser:
    """Базовый класс для парсеров новостей"""
    
    def __init__(
        self,
        source_name: str,
        base_url: str,
        headers: Optional[Dict] = None,
        parse_period_hours: int = 24,
        enable_duplicate_check: bool = True,
        enable_classification: bool = True,
        enable_preprocessing: bool = True,
        min_confidence: float = 0.15
    ):
        """
        Args:
            source_name: Название источника (lenta, rbc, gazeta и т.д.)
            base_url: Базовый URL сайта
            headers: HTTP заголовки для requests
            parse_period_hours: Период парсинга в часах (по умолчанию 24)
            enable_duplicate_check: Включить проверку дубликатов
            enable_classification: Включить классификацию
            enable_preprocessing: Включить предобработку текста
            min_confidence: Минимальная уверенность классификации
        """
        self.source_name = source_name
        self.base_url = base_url
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.parse_period_hours = parse_period_hours
        self.enable_duplicate_check = enable_duplicate_check
        self.enable_classification = enable_classification
        self.enable_preprocessing = enable_preprocessing
        self.min_confidence = min_confidence
        
        # Статистика
        self.stats = {
            'total_found': 0,
            'duplicates_skipped': 0,
            'low_confidence_skipped': 0,
            'successfully_saved': 0,
            'errors': 0,
            'by_category': {}
        }
        
        self.client = None
    
    def __enter__(self):
        """Контекстный менеджер - открываем соединение"""
        self.client = get_clickhouse_client()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрываем соединение"""
        if self.client:
            self.client.close()
        
        # Выводим статистику
        self.print_stats()
    
    def fetch_url(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Загружает содержимое URL
        
        Args:
            url: URL для загрузки
            timeout: Таймаут в секундах
            
        Returns:
            HTML содержимое или None
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            print(f"Ошибка загрузки {url}: {e}")
            self.stats['errors'] += 1
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """
        Парсит HTML с помощью BeautifulSoup
        
        Args:
            html: HTML строка
            
        Returns:
            BeautifulSoup объект
        """
        return BeautifulSoup(html, 'html.parser')
    
    def preprocess_article(self, title: str, content: str) -> Tuple[str, str]:
        """
        Предобрабатывает статью
        
        Args:
            title: Заголовок
            content: Содержимое
            
        Returns:
            Tuple (cleaned_title, cleaned_content)
        """
        if not self.enable_preprocessing:
            return title, content
        
        return preprocessor.preprocess_article(title, content)
    
    def classify_article(self, title: str, content: str) -> Tuple[Optional[str], float, Dict]:
        """
        Классифицирует статью
        
        Args:
            title: Заголовок
            content: Содержимое
            
        Returns:
            Tuple (category, confidence, all_scores)
        """
        if not self.enable_classification:
            return None, 0.0, {}
        
        return classifier.classify(title, content)
    
    def check_duplicate(
        self,
        title: str,
        content: str,
        link: str,
        table_name: str
    ) -> Tuple[bool, str]:
        """
        Проверяет статью на дубликат
        
        Args:
            title: Заголовок
            content: Содержимое
            link: URL
            table_name: Таблица для проверки
            
        Returns:
            Tuple (is_duplicate, reason)
        """
        if not self.enable_duplicate_check:
            return False, ""
        
        with create_duplicate_checker() as checker:
            return checker.is_duplicate(title, content, link, table_name)
    
    def save_article(
        self,
        title: str,
        content: str,
        link: str,
        category: str,
        table_name: str,
        published_date: Optional[datetime] = None,
        rubric: str = "",
        confidence: float = 1.0
    ) -> bool:
        """
        Сохраняет статью в базу данных с анализом тональности
        
        Args:
            title: Заголовок
            content: Содержимое
            link: URL
            category: Категория
            table_name: Таблица для сохранения
            published_date: Дата публикации
            rubric: Рубрика
            confidence: Уверенность классификации
            
        Returns:
            True если успешно сохранено
        """
        if not self.client:
            print("Ошибка: соединение с БД не установлено")
            return False
        
        try:
            # Анализируем тональность текста
            sentiment_data = {
                'sentiment_score': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
            
            if SENTIMENT_ANALYZER_AVAILABLE:
                try:
                    analyzer = get_ukraine_sentiment_analyzer()
                    text_for_analysis = f"{title} {content}"
                    sentiment_result = analyzer.analyze_sentiment(text_for_analysis)
                    
                    sentiment_data = {
                        'sentiment_score': sentiment_result.get('sentiment_score', 0.0),
                        'positive_score': sentiment_result.get('positive_score', 0.0),
                        'negative_score': sentiment_result.get('negative_score', 0.0)
                    }
                except Exception as e:
                    print(f"Warning: Sentiment analysis failed: {e}")
            
            # Формируем данные для вставки
            insert_data = {
                'title': title,
                'link': link,
                'content': content,
                'rubric': rubric,
                'source': self.source_name,
                'category': category,
                'published_date': published_date or datetime.now(),
                **sentiment_data
            }
            
            # SQL запрос с полями sentiment
            query = f"""
            INSERT INTO news.{table_name}
            (title, link, content, rubric, source, category, published_date, sentiment_score, positive_score, negative_score)
            VALUES
            (%(title)s, %(link)s, %(content)s, %(rubric)s, %(source)s, %(category)s, %(published_date)s, %(sentiment_score)s, %(positive_score)s, %(negative_score)s)
            """
            
            self.client.execute(query, insert_data)
            
            # Обновляем статистику
            self.stats['successfully_saved'] += 1
            self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1
            
            return True
            
        except Exception as e:
            print(f"Ошибка сохранения статьи '{title[:50]}...': {e}")
            self.stats['errors'] += 1
            return False
    
    def process_article(
        self,
        title: str,
        content: str,
        link: str,
        rubric: str = "",
        published_date: Optional[datetime] = None
    ) -> bool:
        """
        Полный цикл обработки статьи:
        1. Предобработка
        2. Проверка дубликатов
        3. Классификация
        4. Сохранение
        
        Args:
            title: Заголовок
            content: Содержимое
            link: URL
            rubric: Рубрика
            published_date: Дата публикации
            
        Returns:
            True если статья успешно обработана и сохранена
        """
        self.stats['total_found'] += 1
        
        # 1. Предобработка
        clean_title, clean_content = self.preprocess_article(title, content)
        
        # 2. Классификация
        category, confidence, scores = self.classify_article(clean_title, clean_content)
        
        if category is None or confidence < self.min_confidence:
            print(f"❌ Пропущено (низкая уверенность {confidence:.2f}): {clean_title[:60]}...")
            self.stats['low_confidence_skipped'] += 1
            return False
        
        # Пропускаем статьи с категорией 'other' - они не нужны в БД
        if category == 'other':
            print(f"❌ Пропущено (категория 'other'): {clean_title[:60]}...")
            self.stats['low_confidence_skipped'] += 1
            return False
        
        # 3. Определяем таблицу для сохранения
        # Сначала пробуем категорийную таблицу
        category_table = f"{self.source_name}_{category}"
        
        # 4. Проверка дубликатов (в категорийной таблице)
        is_dup, dup_reason = self.check_duplicate(
            clean_title,
            clean_content,
            link,
            category_table
        )
        
        if is_dup:
            print(f"⚠️  Дубликат: {clean_title[:60]}... ({dup_reason})")
            self.stats['duplicates_skipped'] += 1
            return False
        
        # Также проверяем в основной таблице источника
        headlines_table = f"{self.source_name}_headlines"
        is_dup_main, _ = self.check_duplicate(
            clean_title,
            clean_content,
            link,
            headlines_table
        )
        
        if is_dup_main:
            print(f"⚠️  Дубликат в основной таблице: {clean_title[:60]}...")
            self.stats['duplicates_skipped'] += 1
            return False
        
        # 5. Сохраняем в обе таблицы
        success_category = self.save_article(
            clean_title,
            clean_content,
            link,
            category,
            category_table,
            published_date,
            rubric,
            confidence
        )
        
        success_main = self.save_article(
            clean_title,
            clean_content,
            link,
            category,
            headlines_table,
            published_date,
            rubric,
            confidence
        )
        
        if success_category and success_main:
            print(f"✅ Сохранено ({category}, {confidence:.2f}): {clean_title[:60]}...")
            return True
        
        return False
    
    def get_cutoff_date(self) -> datetime:
        """
        Возвращает дату отсечки для парсинга
        
        Returns:
            Datetime объект
        """
        return datetime.now() - timedelta(hours=self.parse_period_hours)
    
    def print_stats(self):
        """Выводит статистику парсинга"""
        print("\n" + "=" * 60)
        print(f"📊 СТАТИСТИКА ПАРСИНГА: {self.source_name.upper()}")
        print("=" * 60)
        print(f"🔍 Найдено статей: {self.stats['total_found']}")
        print(f"✅ Успешно сохранено: {self.stats['successfully_saved']}")
        print(f"⚠️  Пропущено дубликатов: {self.stats['duplicates_skipped']}")
        print(f"❌ Низкая уверенность: {self.stats['low_confidence_skipped']}")
        print(f"🚫 Ошибок: {self.stats['errors']}")
        
        if self.stats['by_category']:
            print("\n📑 По категориям:")
            for cat, count in sorted(self.stats['by_category'].items()):
                print(f"  - {cat}: {count}")
        
        print("=" * 60 + "\n")
    
    def parse(self):
        """
        Основной метод парсинга - должен быть переопределен в дочерних классах
        """
        raise NotImplementedError("Метод parse() должен быть реализован в дочернем классе")

