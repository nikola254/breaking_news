#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный адаптивный парсер новостей с краулером

Этот модуль содержит функции для:
- Универсального парсинга новостных сайтов
- Автоматического обнаружения структуры сайта
- Краулинга по ссылкам
- Адаптивного извлечения контента
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
import logging
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Set
import json
from dataclasses import dataclass

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from parsers.news_categories import classify_news, create_custom_site_tables, get_site_table_name

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("universal_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SiteConfig:
    """Конфигурация для парсинга конкретного сайта"""
    name: str
    base_url: str
    article_selectors: List[str]  # CSS селекторы для поиска статей
    title_selectors: List[str]    # CSS селекторы для заголовков
    content_selectors: List[str]  # CSS селекторы для контента
    link_selectors: List[str]     # CSS селекторы для ссылок
    exclude_patterns: List[str]   # Паттерны для исключения
    max_depth: int = 2           # Максимальная глубина краулинга
    delay_range: tuple = (1, 3)  # Диапазон задержек между запросами
    headers: Dict[str, str] = None

class UniversalParser:
    """Универсальный парсер новостей с краулером"""
    
    def __init__(self):
        self.session = requests.Session()
        self.visited_urls: Set[str] = set()
        self.parsed_articles: List[Dict] = []
        self.client = None
        self._setup_clickhouse()
        
    def _setup_clickhouse(self):
        """Настройка подключения к ClickHouse"""
        try:
            self.client = Client(
                host=Config.CLICKHOUSE_HOST,
                port=Config.CLICKHOUSE_NATIVE_PORT,
                user=Config.CLICKHOUSE_USER,
                password=Config.CLICKHOUSE_PASSWORD
            )
            # Создаем базу данных если не существует
            self.client.execute('CREATE DATABASE IF NOT EXISTS news')
            self._create_universal_table()
        except Exception as e:
            logger.error(f"Ошибка подключения к ClickHouse: {e}")
            
    def _create_universal_table(self):
        """Создание универсальной таблицы для хранения новостей"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS news.universal_news (
            id UUID DEFAULT generateUUIDv4(),
            site_name String,
            url String,
            title String,
            content String,
            category String,
            published_date DateTime DEFAULT now(),
            parsed_date DateTime DEFAULT now(),
            language String DEFAULT 'unknown',
            tags Array(String) DEFAULT [],
            metadata String DEFAULT '{}'
        ) ENGINE = MergeTree()
        ORDER BY (site_name, parsed_date)
        """
        self.client.execute(create_table_query)
        self._create_universal_category_tables()
        
    def _create_universal_category_tables(self):
        """Создание стандартных таблиц категорий для универсального парсера"""
        categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
        
        try:
            for category in categories:
                self.client.execute(f'''
                    CREATE TABLE IF NOT EXISTS news.universal_{category} (
                        id UUID DEFAULT generateUUIDv4(),
                        title String,
                        link String,
                        content String,
                        source String,
                        category String DEFAULT '{category}',
                        parsed_date DateTime DEFAULT now()
                    ) ENGINE = MergeTree()
                    ORDER BY (parsed_date, id)
                ''')
            
            logger.info("Стандартные таблицы категорий созданы успешно")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц категорий: {e}")
        
    def get_default_configs(self) -> Dict[str, SiteConfig]:
        """Получение конфигураций по умолчанию для популярных новостных сайтов"""
        return {
            'bbc': SiteConfig(
                name='BBC News',
                base_url='https://www.bbc.com/news',
                article_selectors=['article', '.gs-c-promo', '.media-list__item'],
                title_selectors=['h1', 'h2', 'h3', '.gs-c-promo-heading__title', '.media-list__title'],
                content_selectors=['.story-body__inner', '.qa-story-body', 'article p'],
                link_selectors=['a[href*="/news/"]', 'a[href*="/sport/"]'],
                exclude_patterns=['/live/', '/weather/', '/iplayer/']
            ),
            'cnn': SiteConfig(
                name='CNN',
                base_url='https://edition.cnn.com',
                article_selectors=['.container__item', '.cd__content'],
                title_selectors=['h1', 'h2', 'h3', '.cd__headline'],
                content_selectors=['.zn-body__paragraph', 'article p'],
                link_selectors=['a[href*="/2024/"]', 'a[href*="/2025/"]'],
                exclude_patterns=['/videos/', '/live-news/', '/weather/']
            ),
            'reuters': SiteConfig(
                name='Reuters',
                base_url='https://www.reuters.com',
                article_selectors=['.story-card', '.media-story-card'],
                title_selectors=['h1', 'h2', 'h3', '.story-title'],
                content_selectors=['.StandardArticleBody_body', 'article p'],
                link_selectors=['a[href*="/world/"]', 'a[href*="/business/"]'],
                exclude_patterns=['/graphics/', '/video/']
            ),
            'euronews': SiteConfig(
                name='Euronews',
                base_url='https://www.euronews.com',
                article_selectors=['.o-block-listing__item', '.m-object--article'],
                title_selectors=['h1', 'h2', 'h3', '.c-article-content__title'],
                content_selectors=['.c-article-content__body', 'article p'],
                link_selectors=['a[href*="/news/"]', 'a[href*="/world/"]'],
                exclude_patterns=['/programmes/', '/live/']
            )
        }
        
    def auto_detect_structure(self, url: str) -> SiteConfig:
        """Автоматическое определение структуры сайта"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Определяем домен
            domain = urlparse(url).netloc.lower()
            
            # Пытаемся найти общие селекторы для новостных сайтов
            article_selectors = []
            title_selectors = []
            content_selectors = []
            link_selectors = []
            
            # Поиск статей
            for selector in ['article', '.article', '.news-item', '.story', '.post']:
                if soup.select(selector):
                    article_selectors.append(selector)
                    
            # Поиск заголовков
            for selector in ['h1', 'h2', 'h3', '.title', '.headline', '.header']:
                if soup.select(selector):
                    title_selectors.append(selector)
                    
            # Поиск контента
            for selector in ['p', '.content', '.body', '.text', 'article p']:
                if soup.select(selector):
                    content_selectors.append(selector)
                    
            # Поиск ссылок на статьи
            links = soup.find_all('a', href=True)
            for link in links[:20]:  # Анализируем первые 20 ссылок
                href = link.get('href')
                if href and any(keyword in href.lower() for keyword in ['news', 'article', 'story', 'post']):
                    link_selectors.append(f'a[href*="{keyword}"]')
                    
            return SiteConfig(
                name=domain,
                base_url=url,
                article_selectors=article_selectors or ['article', 'div'],
                title_selectors=title_selectors or ['h1', 'h2', 'h3'],
                content_selectors=content_selectors or ['p'],
                link_selectors=list(set(link_selectors)) or ['a'],
                exclude_patterns=['/video/', '/live/', '/weather/', '/sport/']
            )
            
        except Exception as e:
            logger.error(f"Ошибка автоопределения структуры для {url}: {e}")
            # Возвращаем базовую конфигурацию
            return SiteConfig(
                name=urlparse(url).netloc,
                base_url=url,
                article_selectors=['article', 'div'],
                title_selectors=['h1', 'h2', 'h3'],
                content_selectors=['p'],
                link_selectors=['a'],
                exclude_patterns=[]
            )
            
    def extract_article_content(self, url: str, config: SiteConfig) -> Optional[Dict]:
        """Извлечение содержимого статьи"""
        try:
            if url in self.visited_urls:
                return None
                
            self.visited_urls.add(url)
            
            # Устанавливаем заголовки если указаны
            headers = config.headers or {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Извлекаем заголовок
            title = None
            for selector in config.title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    break
                    
            if not title:
                title = soup.title.get_text(strip=True) if soup.title else url
                
            # Извлекаем контент
            content_parts = []
            for selector in config.content_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 50:  # Игнорируем короткие фрагменты
                        content_parts.append(text)
                        
            content = ' '.join(content_parts[:10])  # Берем первые 10 абзацев
            
            if not content or len(content) < 100:
                logger.warning(f"Недостаточно контента для {url}")
                return None
                
            # Определяем категорию
            category = classify_news(title, content[:500])
            
            # Определяем язык (простая эвристика)
            language = 'en'  # По умолчанию английский
            if any(char in content for char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
                language = 'ru'
            elif any(char in content for char in 'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'):
                language = 'fr'
                
            return {
                'site_name': config.name,
                'url': url,
                'title': title,
                'content': content,
                'category': category,
                'language': language,
                'metadata': json.dumps({
                    'content_length': len(content),
                    'title_length': len(title),
                    'selectors_used': {
                        'title': [s for s in config.title_selectors if soup.select_one(s)],
                        'content': [s for s in config.content_selectors if soup.select(s)]
                    }
                })
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения контента из {url}: {e}")
            return None
            
    def crawl_site(self, config: SiteConfig, max_articles: int = 50, max_depth: int = None) -> List[Dict]:
        """Краулинг сайта для поиска и парсинга статей"""
        articles = []
        urls_to_visit = [config.base_url]
        depth = 0
        
        # Используем переданную глубину или глубину из конфигурации
        effective_max_depth = max_depth if max_depth is not None else config.max_depth
        
        while urls_to_visit and len(articles) < max_articles and depth < effective_max_depth:
            current_urls = urls_to_visit[:10]  # Обрабатываем по 10 URL за раз
            urls_to_visit = urls_to_visit[10:]
            
            for url in current_urls:
                try:
                    # Задержка между запросами
                    delay = random.uniform(*config.delay_range)
                    time.sleep(delay)
                    
                    # Проверяем исключения
                    if any(pattern in url for pattern in config.exclude_patterns):
                        continue
                        
                    logger.info(f"Парсинг: {url}")
                    
                    # Извлекаем контент статьи
                    article = self.extract_article_content(url, config)
                    if article:
                        articles.append(article)
                        logger.info(f"Добавлена статья: {article['title'][:100]}...")
                        
                    # Ищем новые ссылки для краулинга
                    if depth < effective_max_depth - 1:
                        new_urls = self._find_article_links(url, config)
                        urls_to_visit.extend(new_urls)
                        
                except Exception as e:
                    logger.error(f"Ошибка при обработке {url}: {e}")
                    continue
                    
            depth += 1
            
        logger.info(f"Краулинг завершен. Найдено {len(articles)} статей")
        return articles
        
    def _find_article_links(self, url: str, config: SiteConfig) -> List[str]:
        """Поиск ссылок на статьи на странице"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = set()
            for selector in config.link_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    href = elem.get('href')
                    if href:
                        full_url = urljoin(url, href)
                        if full_url not in self.visited_urls and self._is_valid_article_url(full_url, config):
                            links.add(full_url)
                            
            return list(links)[:20]  # Ограничиваем количество ссылок
            
        except Exception as e:
            logger.error(f"Ошибка поиска ссылок на {url}: {e}")
            return []
            
    def _is_valid_article_url(self, url: str, config: SiteConfig) -> bool:
        """Проверка валидности URL статьи"""
        # Проверяем домен
        if urlparse(url).netloc != urlparse(config.base_url).netloc:
            return False
            
        # Проверяем исключения
        if any(pattern in url for pattern in config.exclude_patterns):
            return False
            
        # Проверяем что это похоже на статью
        article_indicators = ['news', 'article', 'story', 'post', '2024', '2025']
        return any(indicator in url.lower() for indicator in article_indicators)
        
    def save_articles(self, articles: List[Dict], site_url: str = None):
        """Сохранение статей в ClickHouse в стандартные таблицы категорий"""
        if not articles or not self.client:
            return
            
        try:
            # Проверяем существующие URL
            existing_urls = set()
            if articles:
                urls_to_check = [article['url'] for article in articles]
                result = self.client.execute(
                    "SELECT url FROM news.universal_news WHERE url IN %(urls)s",
                    {'urls': urls_to_check}
                )
                existing_urls = {row[0] for row in result}
                
            # Фильтруем новые статьи
            new_articles = [article for article in articles if article['url'] not in existing_urls]
            
            if new_articles:
                # Сохраняем в универсальную таблицу
                self.client.execute(
                    "INSERT INTO news.universal_news (site_name, url, title, content, category, language, metadata) VALUES",
                    new_articles
                )
                
                # Добавляем статьи в стандартные таблицы категорий
                # Группируем статьи по категориям
                articles_by_category = {}
                for article in new_articles:
                    category = article.get('category', 'other')
                    if category not in articles_by_category:
                        articles_by_category[category] = []
                    
                    # Подготавливаем данные для вставки в стандартную таблицу категории
                    article_data = {
                        'title': article['title'],
                        'link': article['url'],
                        'content': article['content'],
                        'source': article['site_name'],
                        'category': category
                    }
                    articles_by_category[category].append(article_data)
                
                # Сохраняем в стандартные таблицы категорий
                for category, category_articles in articles_by_category.items():
                    try:
                        # Сохраняем в стандартную таблицу категории universal_{category}
                        self.client.execute(
                            f"INSERT INTO news.universal_{category} (title, link, content, source, category) VALUES",
                            category_articles
                        )
                        logger.info(f"Сохранено {len(category_articles)} статей в стандартную категорию {category}")
                    except Exception as e:
                        logger.warning(f"Не удалось сохранить в стандартную таблицу universal_{category}: {e}")
                
                logger.info(f"Сохранено {len(new_articles)} новых статей")
            else:
                logger.info("Новых статей для сохранения не найдено")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения статей: {e}")
            
    def parse_site(self, site_identifier: str, max_articles: int = 50, max_depth: int = 2) -> Dict:
        """Парсинг сайта по идентификатору или URL"""
        start_time = time.time()
        
        # Получаем конфигурацию
        default_configs = self.get_default_configs()
        
        if site_identifier in default_configs:
            config = default_configs[site_identifier]
            config.max_depth = max_depth  # Обновляем глубину краулинга
            logger.info(f"Используется предустановленная конфигурация для {config.name}")
        elif site_identifier.startswith('http'):
            config = self.auto_detect_structure(site_identifier)
            config.max_depth = max_depth  # Устанавливаем глубину краулинга
            logger.info(f"Автоопределение структуры для {site_identifier}")
        else:
            raise ValueError(f"Неизвестный сайт: {site_identifier}")
            
        # Краулинг и парсинг
        articles = self.crawl_site(config, max_articles, max_depth)
        
        # Сохранение с передачей URL сайта для автоматического создания таблиц
        site_url = config.base_url if hasattr(config, 'base_url') else site_identifier
        self.save_articles(articles, site_url)
        
        end_time = time.time()
        
        return {
            'site_name': config.name,
            'articles_found': len(articles),
            'execution_time': round(end_time - start_time, 2),
            'articles': articles
        }

def main():
    """Основная функция для тестирования"""
    import argparse
    
    # Настройка парсера аргументов командной строки
    arg_parser = argparse.ArgumentParser(description='Универсальный парсер новостных сайтов')
    arg_parser.add_argument('--url', required=True, help='URL сайта для парсинга')
    arg_parser.add_argument('--max-articles', type=int, default=50, help='Максимальное количество статей для парсинга')
    arg_parser.add_argument('--depth', type=int, default=2, help='Глубина краулинга')
    
    args = arg_parser.parse_args()
    
    # Создание экземпляра парсера
    parser = UniversalParser()
    
    print(f"Запуск универсального парсера для: {args.url}")
    print(f"Максимальное количество статей: {args.max_articles}")
    print(f"Глубина краулинга: {args.depth}")
    
    try:
        # Парсинг указанного сайта
        result = parser.parse_site(args.url, max_articles=args.max_articles)
        print(f"Парсинг {args.url} завершен успешно")
        print(f"Результат парсинга: {result}")
    except Exception as e:
        print(f"Ошибка при парсинге {args.url}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()