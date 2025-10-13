#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер новостей с сайта TSN.ua (Украина)

Этот модуль содержит функции для:
- Парсинга новостей с главной страницы TSN.ua
- Извлечения полного содержимого статей
- Автоматической категоризации новостей
- Сохранения данных в ClickHouse
"""

import requests
from bs4 import BeautifulSoup
from clickhouse_driver import Client
from datetime import datetime
import time
import random
import sys
import os
# Добавляем путь к парсерам для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__)))

from gen_api_classifier import GenApiNewsClassifier
from news_categories import classify_news, create_category_tables
from ukraine_relevance_filter import filter_ukraine_relevance
import sys
import os
import logging

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tsn_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_ukraine_tables_if_not_exists():
    """Создание таблицы в ClickHouse для хранения новостей TSN.ua"""
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Create table if not exists
    client.execute('''
        CREATE TABLE IF NOT EXISTS news.tsn_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            rubric String,
            source String DEFAULT 'tsn.ua',
            category String DEFAULT 'other',
            published_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (published_date, id)
    ''')
    
    # Создаем таблицы для каждой категории
    create_category_tables(client)

def get_article_content(url, headers):
    """Извлечение полного содержимого статьи с TSN.ua"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Поиск основного содержимого статьи
        article_body = soup.find("div", class_="c-card__body")
        
        if not article_body:
            # Альтернативные селекторы
            article_body = soup.find("div", class_="article-content")
            
        if not article_body:
            article_body = soup.find("div", class_="content")
            
        if not article_body:
            return "Не удалось извлечь содержимое статьи"
        
        # Извлечение параграфов
        paragraphs = article_body.find_all("p")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        return content[:5000]  # Ограничиваем размер контента
        
    except Exception as e:
        logger.error(f"Ошибка при получении содержимого статьи {url}: {e}")
        return "Ошибка при получении содержимого статьи"

def parse_tsn_news(limit=None):
    """Основная функция парсинга новостей с TSN.ua"""
    base_url = "https://tsn.ua"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.8,ru-RU;q=0.6,ru;q=0.4,en-US;q=0.2,en;q=0.1",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info(f"Успешно получена главная страница TSN.ua")
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении данных с TSN.ua: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Поиск новостных блоков на главной странице
    articles = []
    
    # Основные новости
    main_news = soup.find_all("a", class_="c-card__link")
    articles.extend(main_news)
    
    # Новости в блоках
    block_news = soup.find_all("a", class_="c-entry-card__link")
    articles.extend(block_news)
    
    # Дополнительные новости
    additional_news = soup.find_all("a", href=lambda x: x and ('/news/' in x or '/politics/' in x or '/world/' in x))
    articles.extend(additional_news)
    
    if not articles:
        logger.warning("Не найдено новостных статей на главной странице")
        return

    logger.info(f"Найдено {len(articles)} новостных ссылок")

    # Подключение к ClickHouse
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Получение существующих ссылок для избежания дубликатов
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.tsn_headlines'))
    
    new_articles = 0
    
    # Применяем лимит если указан
    if limit:
        articles = articles[:limit]
        logger.info(f"Ограничение парсинга: обрабатываем только {len(articles)} статей")
    
    for article in articles:
        try:
            # Извлечение ссылки
            link = article.get('href')
            if not link:
                continue
                
            if not link.startswith('http'):
                link = base_url + link
            
            # Проверка на дубликаты
            if link in existing_links:
                continue
            
            # Извлечение заголовка
            title_elem = article.find(["span", "h3", "h2", "h1"], class_=lambda x: x and ("title" in x or "headline" in x))
            if not title_elem:
                title_elem = article.find("span", class_="c-card__title")
            if not title_elem:
                title_elem = article
            
            title = title_elem.get_text(strip=True) if title_elem else "Без заголовка"
            
            if len(title) < 10:  # Пропускаем слишком короткие заголовки
                continue
            
            # Определение рубрики из URL
            rubric = "Общие новости"
            if '/politics/' in link:
                rubric = "Политика"
            elif '/world/' in link:
                rubric = "В мире"
            elif '/economics/' in link:
                rubric = "Экономика"
            elif '/society/' in link:
                rubric = "Общество"
            elif '/war/' in link or '/ato/' in link:
                rubric = "Война"
            
            # Получение полного содержимого статьи
            content = get_article_content(link, headers)
            
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
                'INSERT INTO news.tsn_headlines (title, link, content, rubric, source, category, social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata, published_date) VALUES',
                [(title, link, content, rubric, 'tsn.ua', category, social_tension_index, spike_index, ai_category, ai_confidence, 'gen_api_classification', datetime.now())]
            )
            
            # Сохранение в категорийную таблицу с новыми полями
            category_table = f'news.tsn_{category}'
            try:
                client.execute(
                    f'INSERT INTO {category_table} (title, link, content, source, category, published_date, social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata) VALUES',
                    [(title, link, content, 'tsn.ua', category, datetime.now(), social_tension_index, spike_index, ai_category, ai_confidence, 'gen_api_classification')]
                )
            except Exception as e:
                logger.warning(f"Не удалось сохранить в категорийную таблицу {category_table}: {e}")
            
            new_articles += 1
            logger.info(f"Добавлена новость: {title[:50]}... (категория: {category})")
            
            # Задержка между запросами
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.error(f"Ошибка при обработке статьи: {e}")
            continue
    
    logger.info(f"Парсинг завершен. Добавлено {new_articles} новых статей")

def main(limit=None):
    """Главная функция для запуска парсера"""
    try:
        logger.info("Запуск парсера TSN.ua")
        
        # Создание таблиц
        create_ukraine_tables_if_not_exists()
        
        # Парсинг новостей
        parse_tsn_news(limit=limit)
        
        logger.info("Парсер TSN.ua завершил работу")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Критическая ошибка в парсере TSN.ua: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Parser for TSN.ua news')
    parser.add_argument('--limit', type=int, default=None, help='Limit articles to parse (for testing)')
    args = parser.parse_args()
    
    main(limit=args.limit)
