#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер новостей с сайта Reuters.com

Этот модуль содержит функции для:
- Парсинга новостей с главной страницы Reuters.com
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
from news_categories import classify_news, create_category_tables
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
        logging.FileHandler("reuters_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_table_if_not_exists():
    """Создание таблицы в ClickHouse для хранения новостей Reuters.com"""
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
        CREATE TABLE IF NOT EXISTS news.reuters_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            rubric String,
            source String DEFAULT 'reuters.com',
            category String DEFAULT 'other',
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
    ''')
    
    # Создаем таблицы для каждой категории
    create_category_tables(client)

def get_article_content(url, headers):
    """Извлечение полного содержимого статьи с Reuters.com"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Поиск основного содержимого статьи
        article_body = soup.find("div", {"data-module": "ArticleBody"})
        
        if not article_body:
            # Альтернативные селекторы
            article_body = soup.find("div", class_="StandardArticleBody_body")
            
        if not article_body:
            article_body = soup.find("div", class_="ArticleBodyWrapper")
            
        if not article_body:
            return "Не удалось извлечь содержимое статьи"
        
        # Извлечение параграфов
        paragraphs = article_body.find_all("p")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        return content[:5000]  # Ограничиваем размер контента
        
    except Exception as e:
        logger.error(f"Ошибка при получении содержимого статьи {url}: {e}")
        return "Ошибка при получении содержимого статьи"

def parse_reuters_news():
    """Основная функция парсинга новостей с Reuters.com"""
    base_url = "https://www.reuters.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info(f"Успешно получена главная страница Reuters.com")
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении данных с Reuters.com: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Поиск новостных блоков на главной странице
    articles = []
    
    # Основные новости
    main_news = soup.find_all("a", {"data-module": "HeadlineLink"})
    articles.extend(main_news)
    
    # Новости в блоках
    block_news = soup.find_all("a", href=lambda x: x and '/world/' in x)
    articles.extend(block_news)
    
    # Дополнительные новости
    additional_news = soup.find_all("a", href=lambda x: x and ('/business/' in x or '/technology/' in x or '/markets/' in x))
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
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.reuters_headlines'))
    
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
            if '/video/' in link or '/graphics/' in link or '/pictures/' in link:
                continue
            
            # Извлечение заголовка
            title_elem = article.find(["span", "h3", "h2", "h1"])
            if not title_elem:
                title_elem = article
            
            title = title_elem.get_text(strip=True) if title_elem else "Без заголовка"
            
            if len(title) < 10:  # Пропускаем слишком короткие заголовки
                continue
            
            # Определение рубрики из URL
            rubric = "Общие новости"
            if '/world/' in link:
                rubric = "В мире"
            elif '/business/' in link:
                rubric = "Бизнес"
            elif '/technology/' in link:
                rubric = "Технологии"
            elif '/markets/' in link:
                rubric = "Рынки"
            elif '/breakingviews/' in link:
                rubric = "Аналитика"
            elif '/lifestyle/' in link:
                rubric = "Образ жизни"
            elif '/sports/' in link:
                rubric = "Спорт"
            
            # Получение полного содержимого статьи
            content = get_article_content(link, headers)
            
            # Классификация новости
            category = classify_news(title, content)
            
            # Сохранение в основную таблицу
            client.execute(
                'INSERT INTO news.reuters_headlines (title, link, content, rubric, category) VALUES',
                [(title, link, content, rubric, category)]
            )
            
            # Сохранение в категорийную таблицу
            category_table = f'news.telegram_{category}'
            try:
                client.execute(
                    f'INSERT INTO {category_table} (title, content, source, category, channel) VALUES',
                    [(title, content, 'reuters.com', category, 'reuters_com')]
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
    logger.info("Запуск парсера Reuters.com")
    
    # Создание таблиц
    create_table_if_not_exists()
    
    # Парсинг новостей
    parse_reuters_news()
    
    logger.info("Парсер Reuters.com завершил работу")

if __name__ == "__main__":
    main()