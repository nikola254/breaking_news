#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ai_news_classifier import classify_news_ai
from news_categories import classify_news
from ukraine_relevance_filter import filter_ukraine_relevance
"""
Парсер новостей с сайта Euronews.com

Этот модуль содержит функции для:
- Парсинга новостей с главной страницы Euronews.com
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
from parsers.news_categories import classify_news, create_category_tables
import sys
import os
import logging
import re

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("euronews_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_ukraine_tables_if_not_exists():
    """Создание таблицы в ClickHouse для хранения новостей Euronews.com"""
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
        CREATE TABLE IF NOT EXISTS news.euronews_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            rubric String,
            source String DEFAULT 'euronews.com',
            category String DEFAULT 'other',
            published_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (published_date, id)
    ''')
    
    # Создаем таблицы для каждой категории
    create_category_tables(client)

def get_article_content(url, headers):
    """Извлечение полного содержимого статьи с Euronews.com"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Поиск основного содержимого статьи
        article_body = soup.find("div", class_="c-article-content")
        
        if not article_body:
            # Альтернативные селекторы
            article_body = soup.find("div", class_="article__content")
            
        if not article_body:
            article_body = soup.find("div", class_="c-article-body")
            
        if not article_body:
            return "Не удалось извлечь содержимое статьи"
        
        # Извлечение параграфов
        paragraphs = article_body.find_all("p")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        return content[:5000]  # Ограничиваем размер контента
        
    except Exception as e:
        logger.error(f"Ошибка при получении содержимого статьи {url}: {e}")
        return "Ошибка при получении содержимого статьи"

def parse_euronews_news():
    """Основная функция парсинга новостей с Euronews.com"""
    # Попробуем парсить разные разделы новостей
    sections = [
        "https://www.euronews.com/news/europe",
        "https://www.euronews.com/news/international",
        "https://www.euronews.com/business",
        "https://www.euronews.com/my-europe"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    article_links = []
    
    for section_url in sections:
        try:
            logger.info(f"Парсинг раздела: {section_url}")
            response = requests.get(section_url, headers=headers, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Ищем все ссылки на статьи
            links = soup.find_all('a', href=True)
            section_links = []
            
            for link in links:
                href = link.get('href')
                if href:
                    # Ищем ссылки, которые выглядят как новостные статьи
                    if ('/2024/' in href or '/2025/' in href) and not re.search(r'/(tag|programme|video|my-europe|green|next|travel|culture|sport)/', href):
                        section_links.append(link)
                    # Также ищем ссылки с длинными заголовками (характерно для новостей)
                    elif len(href.split('/')[-1]) > 20 and not href.endswith('.html') and not re.search(r'/(tag|programme|video|my-europe|green|next|travel|culture|sport)/', href):
                        section_links.append(link)
            
            logger.info(f"Найдено {len(section_links)} ссылок в разделе {section_url}")
            article_links.extend(section_links)
            
            # Небольшая пауза между запросами
            time.sleep(1)
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении раздела {section_url}: {e}")
            continue
    
    logger.info(f"Всего найдено {len(article_links)} потенциальных новостных ссылок")
    
    # Удаляем дубликаты и обрабатываем ссылки
    articles = []
    seen_urls = set()
    base_url = "https://www.euronews.com"  # Определяем base_url
    
    for link in article_links:
        href = link.get('href')
        if not href:
            continue
            
        # Преобразуем относительные ссылки в абсолютные
        if href.startswith('/'):
            full_url = base_url + href
        elif href.startswith('http'):
            full_url = href
        else:
            continue
            
        # Проверяем, что это действительно ссылка на Euronews
        if 'euronews.com' not in full_url:
            continue
            
        # Избегаем дубликатов
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Создаем объект ссылки с полным URL, сохраняя оригинальные методы
        link_obj = type('obj', (object,), {
            'get': lambda self, attr, url=full_url: url if attr == 'href' else link.get(attr),
            'find': lambda self, *args, **kwargs: link.find(*args, **kwargs) if hasattr(link, 'find') else None,
            'text': getattr(link, 'text', ''),
            'get_text': lambda self, *args, **kwargs: link.get_text(*args, **kwargs) if hasattr(link, 'get_text') else ''
        })()
        articles.append(link_obj)
    
    if not articles:
        logger.warning("Не найдено новостных статей")
        return

    logger.info(f"Обработано {len(articles)} уникальных новостных ссылок")

    # Подключение к ClickHouse
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Получение существующих ссылок для избежания дубликатов
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.euronews_headlines'))
    
    new_articles = 0
    
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
            
            # Пропускаем ссылки, которые не являются новостными статьями
            if '/video/' in link or '/live/' in link or '/sport/' in link:
                continue
            
            # Извлечение заголовка из текста ссылки или из URL
            title = article.get_text(strip=True) if hasattr(article, 'get_text') else ""
            
            # Если заголовок пустой, попробуем извлечь из URL
            if not title or len(title) < 10:
                # Извлекаем заголовок из URL (последняя часть после последнего слеша)
                url_parts = link.rstrip('/').split('/')
                if url_parts:
                    title = url_parts[-1].replace('-', ' ').replace('_', ' ').title()
            
            if len(title) < 10:  # Пропускаем слишком короткие заголовки
                continue
            
            # Определение рубрики из URL
            rubric = "Общие новости"
            if '/world/' in link:
                rubric = "В мире"
            elif '/europe/' in link:
                rubric = "Европа"
            elif '/business/' in link:
                rubric = "Бизнес"
            elif '/tech/' in link:
                rubric = "Технологии"
            elif '/green/' in link:
                rubric = "Экология"
            elif '/culture/' in link:
                rubric = "Культура"
            elif '/health/' in link:
                rubric = "Здоровье"
            elif '/travel/' in link:
                rubric = "Путешествия"
            
            # Получение полного содержимого статьи
            content = get_article_content(link, headers)
            
            # Проверяем релевантность к украинскому конфликту
            logger.info("Проверка релевантности к украинскому конфликту...")
            relevance_result = filter_ukraine_relevance(title, content)
            
            if not relevance_result['is_relevant']:
                logger.info(f"Статья не релевантна украинскому конфликту (score: {relevance_result['relevance_score']:.2f})")
                logger.info("Пропускаем статью...")
                continue
            
            logger.info(f"Статья релевантна (score: {relevance_result['relevance_score']:.2f})")
            logger.info(f"Найденные ключевые слова: {relevance_result['keywords_found']}")
            
            # Используем категорию из результата релевантности
            category = relevance_result.get('category', 'other')
            logger.info(f"Категория: {category}")
            
            # Сохранение в основную таблицу
            client.execute(
                'INSERT INTO news.euronews_headlines (title, link, content, rubric, source, category) VALUES',
                [(title, link, content, rubric, 'euronews.com', category)]
            )
            
            # Сохранение в категорийную таблицу
            category_table = f'news.euronews_{category}'
            try:
                client.execute(
                    f'INSERT INTO {category_table} (title, link, content, source, category, published_date) VALUES',
                    [(title, link, content, 'euronews.com', category, datetime.now())]
                )
            except Exception as e:
                logger.warning(f"Не удалось сохранить в категорийную таблицу {category_table}: {e}")
            
            new_articles += 1
            logger.info(f"Добавлена новость: {title[:50]}... (категория: {category})")
            
            # Задержка между запросами
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            logger.error(f"Ошибка при обработке статьи: {e}")
            continue
    
    logger.info(f"Парсинг завершен. Добавлено {new_articles} новых статей")

def main():
    """Главная функция для запуска парсера"""
    logger.info("Запуск парсера Euronews.com")
    
    # Создание таблиц
    create_ukraine_tables_if_not_exists()
    
    # Парсинг новостей
    parse_euronews_news()
    
    logger.info("Парсер Euronews.com завершил работу")

if __name__ == "__main__":
    main()
