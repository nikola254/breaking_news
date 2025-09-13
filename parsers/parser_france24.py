#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер новостей с сайта France24.com

Этот модуль содержит функции для:
- Парсинга новостей с главной страницы France24.com
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
from ai_news_classifier import classify_news_ai
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
        logging.FileHandler("france24_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_table_if_not_exists():
    """Создание таблицы в ClickHouse для хранения новостей France24.com"""
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
        CREATE TABLE IF NOT EXISTS news.france24_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            rubric String,
            source String DEFAULT 'france24.com',
            category String DEFAULT 'other',
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
    ''')
    
    # Создаем таблицы для каждой категории
    create_category_tables(client)

def get_article_content(url, headers):
    """Извлечение полного содержимого статьи с France24.com"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Поиск основного содержимого статьи
        article_body = soup.find("div", class_="t-content__body")
        
        if not article_body:
            # Альтернативные селекторы
            article_body = soup.find("div", class_="article-body")
            
        if not article_body:
            article_body = soup.find("div", class_="o-article-body")
            
        if not article_body:
            return "Не удалось извлечь содержимое статьи"
        
        # Извлечение параграфов
        paragraphs = article_body.find_all("p")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        return content[:5000]  # Ограничиваем размер контента
        
    except Exception as e:
        logger.error(f"Ошибка при получении содержимого статьи {url}: {e}")
        return "Ошибка при получении содержимого статьи"

def parse_france24_news():
    """Основная функция парсинга новостей с France24.com"""
    base_url = "https://www.france24.com/en"
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
        logger.info(f"Успешно получена главная страница France24.com")
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении данных с France24.com: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Поиск новостных блоков на главной странице
    articles = []
    
    # Основные новости
    main_news = soup.find_all("a", class_="article-link")
    articles.extend(main_news)
    
    # Новости в блоках
    block_news = soup.find_all("a", href=lambda x: x and '/en/' in x and '/news/' in x)
    articles.extend(block_news)
    
    # Дополнительные новости
    additional_news = soup.find_all("h2", class_="article__title")
    for h2 in additional_news:
        link_elem = h2.find_parent("a")
        if link_elem:
            articles.append(link_elem)
    
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
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.france24_headlines'))
    
    new_articles = 0
    
    for article in articles:
        try:
            # Извлечение ссылки
            link = article.get('href')
            if not link:
                continue
                
            if not link.startswith('http'):
                link = "https://www.france24.com" + link
            
            # Проверка на дубликаты
            if link in existing_links:
                continue
            
            # Пропускаем ссылки, которые не являются новостными статьями
            if '/video/' in link or '/live/' in link or '/sports/' in link:
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
            if '/europe/' in link:
                rubric = "Европа"
            elif '/africa/' in link:
                rubric = "Африка"
            elif '/middle-east/' in link:
                rubric = "Ближний Восток"
            elif '/asia-pacific/' in link:
                rubric = "Азиатско-Тихоокеанский регион"
            elif '/americas/' in link:
                rubric = "Америка"
            elif '/france/' in link:
                rubric = "Франция"
            elif '/economy/' in link:
                rubric = "Экономика"
            elif '/environment/' in link:
                rubric = "Экология"
            
            # Получение полного содержимого статьи
            content = get_article_content(link, headers)
            
            # Классификация новости
            try:

                category = classify_news_ai(title, content)

            except Exception as e:

                print(f"AI классификация не удалась: {e}")

                category = classify_news(title, content)
            
            # Сохранение в основную таблицу
            client.execute(
                'INSERT INTO news.france24_headlines (title, link, content, rubric, source, category) VALUES',
                [(title, link, content, rubric, 'france24.com', category)]
            )
            
            # Сохранение в категорийную таблицу
            category_table = f'news.france24_{category}'
            try:
                client.execute(
                    f'INSERT INTO {category_table} (title, link, content, source, category, parsed_date) VALUES',
                    [(title, link, content, 'france24.com', category, datetime.now())]
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
    logger.info("Запуск парсера France24.com")
    
    # Создание таблиц
    create_table_if_not_exists()
    
    # Парсинг новостей
    parse_france24_news()
    
    logger.info("Парсер France24.com завершил работу")

if __name__ == "__main__":
    main()