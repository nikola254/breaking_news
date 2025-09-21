#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример интеграции AI классификатора в парсер новостей
Этот файл показывает, как модифицировать существующие парсеры для использования AI классификации
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from clickhouse_driver import Client
import requests
from bs4 import BeautifulSoup

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к модулям
sys.path.append(os.path.dirname(__file__))

# Импортируем AI классификатор
from ai_news_classifier import classify_news_ai
from news_categories import classify_news  # Fallback классификатор

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Конфигурация для подключения к ClickHouse"""
    CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_NATIVE_PORT = int(os.getenv('CLICKHOUSE_NATIVE_PORT', 9000))
    CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')

def get_article_content(url: str, headers: dict) -> str:
    """Получение полного содержимого статьи
    
    Args:
        url (str): URL статьи
        headers (dict): HTTP заголовки
        
    Returns:
        str: Содержимое статьи
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Удаляем ненужные элементы
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Ищем основной контент
        content_selectors = [
            'article',
            '.article-content',
            '.content',
            '.post-content',
            '.entry-content',
            'main',
            '.main-content'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True, separator=' ')
                break
        
        # Если не нашли специфичные селекторы, берем все параграфы
        if not content:
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        return content[:5000]  # Ограничиваем длину
        
    except Exception as e:
        logger.error(f"Ошибка при получении содержимого {url}: {e}")
        return ""

def classify_with_ai_fallback(title: str, content: str, use_ai: bool = True) -> str:
    """Классификация с AI и fallback на ключевые слова
    
    Args:
        title (str): Заголовок новости
        content (str): Содержимое новости
        use_ai (bool): Использовать ли AI классификацию
        
    Returns:
        str: Категория новости
    """
    if use_ai:
        try:
            # Пробуем AI классификацию
            category = classify_news_ai(title, content)
            logger.info(f"AI классификация: {category}")
            return category
        except Exception as e:
            logger.warning(f"AI классификация не удалась: {e}")
            logger.info("Переключаемся на классификацию по ключевым словам")
    
    # Fallback на классификацию по ключевым словам
    category = classify_news(title, content)
    logger.info(f"Классификация по ключевым словам: {category}")
    return category

def parse_example_news_site():
    """Пример парсинга новостного сайта с AI классификацией"""
    
    logger.info("Начинаем парсинг с AI классификацией")
    
    # Проверяем доступность AI API
    ai_available = os.getenv('API_KEY') is not None
    logger.info(f"AI классификация доступна: {ai_available}")
    
    # Заголовки для запросов
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Подключение к ClickHouse
    try:
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        logger.info("Подключение к ClickHouse установлено")
    except Exception as e:
        logger.error(f"Ошибка подключения к ClickHouse: {e}")
        return
    
    # Тестовые данные (в реальном парсере здесь был бы код парсинга сайта)
    test_articles = [
        {
            'title': 'Украина получила новую военную помощь от НАТО',
            'link': 'https://example.com/ukraine-nato-aid',
            'content': 'НАТО объявило о предоставлении Украине дополнительного пакета военной помощи. Альянс передаст современные системы ПВО и боеприпасы для защиты от российских атак.'
        },
        {
            'title': 'Новые санкции ЕС против России вступили в силу',
            'link': 'https://example.com/eu-sanctions',
            'content': 'Европейский союз ввел новый пакет санкций против российских компаний и чиновников. Ограничения коснулись энергетического и технологического секторов.'
        },
        {
            'title': 'Apple представила новый iPhone 15',
            'link': 'https://example.com/iphone-15',
            'content': 'Компания Apple официально представила новую линейку смартфонов iPhone 15. Устройства получили улучшенные камеры и более мощный процессор.'
        }
    ]
    
    # Создаем таблицу для примера (если не существует)
    try:
        client.execute('''
            CREATE TABLE IF NOT EXISTS news.ai_classified_news (
                id UInt64,
                title String,
                link String,
                content String,
                source String,
                category String,
                classification_method String,
                published_date DateTime
            ) ENGINE = MergeTree()
            ORDER BY published_date
        ''')
        logger.info("Таблица ai_classified_news готова")
    except Exception as e:
        logger.error(f"Ошибка создания таблицы: {e}")
        return
    
    # Обрабатываем статьи
    processed_count = 0
    ai_classified_count = 0
    
    for article in test_articles:
        try:
            title = article['title']
            link = article['link']
            content = article['content']
            
            logger.info(f"Обрабатываем: {title}")
            
            # Классифицируем статью
            category = classify_with_ai_fallback(title, content, use_ai=ai_available)
            
            # Определяем метод классификации
            classification_method = 'ai' if ai_available else 'keywords'
            if ai_available:
                ai_classified_count += 1
            
            # Сохраняем в базу данных
            client.execute(
                'INSERT INTO news.ai_classified_news (id, title, link, content, source, category, classification_method, published_date) VALUES',
                [(processed_count + 1, title, link, content, 'example.com', category, classification_method, datetime.now())]
            )
            
            processed_count += 1
            logger.info(f"Статья сохранена с категорией: {category}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки статьи {article['title']}: {e}")
    
    # Статистика
    logger.info(f"\n=== СТАТИСТИКА ПАРСИНГА ===")
    logger.info(f"Обработано статей: {processed_count}")
    logger.info(f"Классифицировано через AI: {ai_classified_count}")
    logger.info(f"Классифицировано через ключевые слова: {processed_count - ai_classified_count}")
    
    # Показываем результаты из базы
    try:
        results = client.execute(
            'SELECT title, category, classification_method FROM news.ai_classified_news ORDER BY published_date DESC LIMIT 10'
        )
        
        logger.info("\n=== ПОСЛЕДНИЕ КЛАССИФИЦИРОВАННЫЕ СТАТЬИ ===")
        for title, category, method in results:
            logger.info(f"{title[:50]}... -> {category} ({method})")
            
    except Exception as e:
        logger.error(f"Ошибка получения результатов: {e}")

if __name__ == "__main__":
    parse_example_news_site()
