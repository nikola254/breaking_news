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
from parsers.gen_api_classifier import GenApiNewsClassifier
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
        
        try:
            classifier = GenApiNewsClassifier()
            result = classifier.classify(title, content)
            
            return result['category_name'], result['confidence'], {
                'social_tension_index': result['social_tension_index'],
                'spike_index': result['spike_index']
            }
        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return None, 0.0, {}
    
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
        Сохраняет статью в базу данных с анализом тональности и валидацией контента
        
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
            # Валидация контента
            from parsers.content_validator import ContentValidator
            
            validator = ContentValidator()
            source_domain = self._extract_domain(link)
            is_valid, cleaned_content = validator.validate_content(content, source_domain)
            
            if not is_valid:
                print(f"Статья отклонена валидатором: {cleaned_content}")
                self.stats['validation_rejected'] = self.stats.get('validation_rejected', 0) + 1
                return False
            
            # Используем очищенный контент
            content = cleaned_content
            
            # AI-классификация и расчет индексов напряженности
            ai_data = self._perform_ai_classification(title, content)
            
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
                'content_validated': 1,  # Флаг валидации контента
                **sentiment_data,
                **ai_data
            }
            
            # SQL запрос с полями sentiment, валидации и AI-классификации
            query = f"""
            INSERT INTO news.{table_name}
            (title, link, content, rubric, source, category, published_date, sentiment_score, positive_score, negative_score, content_validated, social_tension_index, spike_index, ai_classification_metadata, ai_category, ai_confidence)
            VALUES
            (%(title)s, %(link)s, %(content)s, %(rubric)s, %(source)s, %(category)s, %(published_date)s, %(sentiment_score)s, %(positive_score)s, %(negative_score)s, %(content_validated)s, %(social_tension_index)s, %(spike_index)s, %(ai_classification_metadata)s, %(ai_category)s, %(ai_confidence)s)
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
    
    def _extract_domain(self, url: str) -> str:
        """
        Извлекает домен из URL
        
        Args:
            url: URL для извлечения домена
            
        Returns:
            str: Домен
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""
    
    def _perform_ai_classification(self, title: str, content: str) -> dict:
        """
        Выполняет AI-классификацию новости и расчет индексов напряженности
        
        Args:
            title: Заголовок новости
            content: Содержимое новости
            
        Returns:
            dict: Данные AI-классификации
        """
        try:
            # Используем Gen-API классификатор
            classifier = GenApiNewsClassifier()
            result = classifier.classify(title, content)
            
            # Формируем метаданные
            metadata = {
                'gen_api_category': result['category_name'],
                'gen_api_category_id': result['category_id'],
                'gen_api_confidence': result['confidence'],
                'processing_time': 'gen_api',
                'cached': result.get('cached', False)
            }
            
            return {
                'social_tension_index': result['social_tension_index'],
                'spike_index': result['spike_index'],
                'ai_classification_metadata': str(metadata),
                'ai_category': result['category_name'],
                'ai_confidence': result['confidence']
            }
            
        except Exception as e:
            print(f"Warning: AI classification failed: {e}")
            
            # Fallback: используем только ручной расчет индексов
            try:
                from parsers.tension_calculator import calculate_both_indices
                
                # Используем категорию по умолчанию
                default_category = 'information_social'
                social_tension, spike_index = calculate_both_indices(
                    default_category, title, content
                )
                
                metadata = {
                    'fallback': True,
                    'error': str(e),
                    'default_category': default_category
                }
                
                return {
                    'social_tension_index': social_tension,
                    'spike_index': spike_index,
                    'ai_classification_metadata': str(metadata),
                    'ai_category': default_category,
                    'ai_confidence': 0.1  # Низкая уверенность для fallback
                }
                
            except Exception as e2:
                print(f"Warning: Fallback classification also failed: {e2}")
                
                # Последний fallback: нулевые значения
                return {
                    'social_tension_index': 0.0,
                    'spike_index': 0.0,
                    'ai_classification_metadata': f"{{'error': '{str(e2)}', 'fallback': True}}",
                    'ai_category': 'unknown',
                    'ai_confidence': 0.0
                }
    
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

