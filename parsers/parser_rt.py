#!/usr/bin/env python3
"""
Парсер новостей с сайта RT.com
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from clickhouse_driver import Client

# Добавляем путь к парсерам для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__)))
from gen_api_classifier import GenApiNewsClassifier
from ukraine_relevance_filter import filter_ukraine_relevance

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_clickhouse_client():
    """Создает клиент ClickHouse с retry логикой"""
    import time
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Добавляем корневую директорию проекта в sys.path для импорта config
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from config import Config
            
            # Используем NATIVE_PORT для более стабильного подключения
            client = Client(
                host=Config.CLICKHOUSE_HOST,
                port=Config.CLICKHOUSE_NATIVE_PORT or Config.CLICKHOUSE_PORT,
                user=Config.CLICKHOUSE_USER,
                password=Config.CLICKHOUSE_PASSWORD
            )
            
            # Тестируем подключение
            client.execute('SELECT 1')
            logger.info(f"ClickHouse подключение успешно (попытка {attempt + 1})")
            return client
            
        except Exception as e:
            logger.warning(f"Попытка подключения к ClickHouse {attempt + 1}/{max_retries} неудачна: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Экспоненциальная задержка: 1s, 2s, 4s
                logger.info(f"Ожидание {wait_time} секунд перед повторной попыткой...")
                time.sleep(wait_time)
            else:
                logger.error(f"Не удалось подключиться к ClickHouse после {max_retries} попыток")
                return None

def get_article_content(url, headers):
    """Получает содержимое статьи по URL"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем основной контент статьи
        content_div = soup.find('div', class_='article__text')
        if not content_div:
            content_div = soup.find('div', class_='article-text')
        
        if content_div:
            paragraphs = content_div.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            return content.strip()
        
        return "Не удалось извлечь содержимое статьи"
    except Exception as e:
        logger.error(f"Ошибка получения контента статьи {url}: {e}")
        return "Ошибка получения содержимого"

def parse_rbc_news(limit=None):
    """Парсит новости с RBC.ru"""
    try:
        client = get_clickhouse_client()
        if not client:
            logger.error("Не удалось подключиться к ClickHouse")
            return 0
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        url = "https://russian.rt.com/"
        logger.info(f"Получение новостей с {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем ссылки на новости
        news_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/news/' in href and href not in news_links:
                if href.startswith('/'):
                    href = 'https://russian.rt.com' + href
                news_links.append(href)
        
        logger.info(f"Найдено {len(news_links)} новостных ссылок")
        
        if limit:
            news_links = news_links[:limit]
            logger.info(f"Ограничение парсинга: обрабатываем только {len(news_links)} статей")
        
        new_count = 0
        
        for link in news_links:
            try:
                # Получаем заголовок
                title_elem = soup.find('a', href=link.replace('https://russian.rt.com', ''))
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title:
                    continue
                
                # Получение полного содержимого статьи
                content = get_article_content(link, headers)
                
                # Проверка контента перед сохранением
                if not content or len(content.strip()) < 100:
                    logger.warning(f"Пропуск статьи '{title}' - недостаточно контента (длина: {len(content) if content else 0})")
                    continue
                
                # Проверяем релевантность к украинскому конфликту
                logger.info("Проверка релевантности к украинскому конфликту...")
                relevance_result = filter_ukraine_relevance(title, content)
                
                if not relevance_result['is_relevant']:
                    logger.info(f"Статья не релевантна украинскому конфликту (score: {relevance_result['relevance_score']:.2f})")
                    continue
                
                logger.info(f"Статья релевантна (score: {relevance_result['relevance_score']:.2f}, категория: {relevance_result['category']})")
                logger.info(f"Найденные ключевые слова: {relevance_result['keywords_found']}")
                
                # Дополнительная классификация через Gen-API для получения индексов напряженности
                try:
                    classifier = GenApiNewsClassifier()
                    ai_result = classifier.classify(title, content)
                    
                    # Используем результаты Gen-API классификации
                    category = ai_result['category_name']
                    social_tension_index = ai_result['social_tension_index']
                    spike_index = ai_result['spike_index']
                    ai_confidence = ai_result['confidence']
                    ai_category = ai_result['category_name']
                    
                    logger.info(f"Gen-API классификация: {category} (напряженность: {social_tension_index}, всплеск: {spike_index})")
                    
                except Exception as e:
                    logger.warning(f"Ошибка Gen-API классификации: {e}")
                    # Fallback к результатам фильтра релевантности
                    category = relevance_result.get('category', 'other')
                    social_tension_index = 0.0
                    spike_index = 0.0
                    ai_confidence = 0.0
                    ai_category = category

                if not category or category is None:
                    category = 'other'
                
                # Пропускаем статьи с категорией 'other' - они не нужны в БД
                if category == 'other':
                    logger.info(f"Пропущено (категория 'other'): {title[:50]}...")
                    continue
                
                # Сохранение в основную таблицу с новыми полями
                client.execute(
                    'INSERT INTO news.rt_headlines (title, link, content, source, category, social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata, published_date) VALUES',
                    [(title, link, content, 'rt.com', category, social_tension_index, spike_index, ai_category, ai_confidence, 'gen_api_classification', datetime.now())]
                )
                
                logger.info(f"Добавлена статья: {title[:50]}...")
                new_count += 1
                
            except Exception as e:
                logger.error(f"Ошибка обработки статьи {link}: {e}")
                continue
        
        logger.info(f"Парсинг завершен. Добавлено {new_count} новых статей")
        return new_count
        
    except Exception as e:
        logger.error(f"Ошибка парсинга RT.com: {e}")
        return 0

def main(limit=None):
    """Основная функция"""
    try:
        logger.info("Запуск парсера RT.com")
        new_count = parse_rbc_news(limit=limit)
        logger.info(f"Парсер RT.com завершил работу")
        return new_count
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Parser for RT.com news')
    parser.add_argument('--limit', type=int, default=None, help='Limit articles to parse (for testing)')
    args = parser.parse_args()
    
    result = main(limit=args.limit)
    sys.exit(0 if result > 0 else 1)
