#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный парсер Gazeta.ru - работает без сложных зависимостей
"""
import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clickhouse_driver import Client
from config import Config
from parsers.news_preprocessor import preprocessor
from parsers.improved_classifier import classifier


class SimpleGazetaParser:
    """Упрощенный парсер Gazeta.ru"""
    
    def __init__(self, parse_period_hours: int = 24):
        self.source_name = 'gazeta'
        self.base_url = 'https://www.gazeta.ru'
        self.parse_period_hours = parse_period_hours
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.stats = {
            'total_found': 0,
            'duplicates_skipped': 0,
            'low_confidence_skipped': 0,
            'successfully_saved': 0,
            'errors': 0,
            'by_category': {}
        }
        
        self.client = None
        self.seen_links = set()
    
    def connect_db(self):
        """Подключение к БД"""
        self.client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=Config.CLICKHOUSE_DATABASE
        )
    
    def close_db(self):
        """Закрытие соединения"""
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
    
    def get_article_content(self, url: str) -> str:
        """Получает содержимое статьи"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Пробуем разные селекторы для Gazeta.ru
            body = None
            
            # Новый селектор
            body = soup.find('div', class_='article_text_wrapper')
            
            if not body:
                body = soup.find('div', class_='b_article-text')
            
            if not body:
                body = soup.find('div', class_='article_text')
            
            if not body:
                body = soup.find('div', {'itemprop': 'articleBody'})
            
            if not body:
                # Пробуем article tag
                body = soup.find('article')
            
            if not body:
                return ""
            
            # Извлекаем параграфы
            paragraphs = body.find_all('p')
            if not paragraphs:
                # Если параграфов нет, берем весь текст
                content = body.get_text(strip=True)
            else:
                content = "\n\n".join([
                    p.get_text(strip=True)
                    for p in paragraphs
                    if p.get_text(strip=True) and len(p.get_text(strip=True)) > 10
                ])
            
            return content[:5000]
            
        except Exception as e:
            print(f"⚠️  Ошибка загрузки статьи: {e}")
            return ""
    
    def is_duplicate_simple(self, link: str) -> bool:
        """Простая проверка дубликатов"""
        if link in self.seen_links:
            return True
        
        if self.client:
            try:
                query = """
                SELECT count(*) as cnt
                FROM news.gazeta_headlines
                WHERE link = %(link)s
                """
                result = self.client.execute(query, {'link': link})
                if result and result[0][0] > 0:
                    return True
            except Exception as e:
                print(f"⚠️  Ошибка проверки дубликата: {e}")
        
        return False
    
    def save_article(self, title: str, content: str, link: str, category: str, rubric: str = ""):
        """Сохраняет статью в БД"""
        if not self.client:
            print("❌ Нет подключения к БД")
            self.stats['errors'] += 1
            return False
        
        try:
            data = {
                'title': title,
                'link': link,
                'content': content,
                'rubric': rubric,
                'source': self.source_name,
                'category': category,
                'published_date': datetime.now()
            }
            
            # Основная таблица
            query_main = """
            INSERT INTO news.gazeta_headlines
            (title, link, content, rubric, source, category, published_date)
            VALUES
            (%(title)s, %(link)s, %(content)s, %(rubric)s, %(source)s, %(category)s, %(published_date)s)
            """
            
            self.client.execute(query_main, data)
            
            # Категорийная таблица
            category_table = f"gazeta_{category}"
            query_category = f"""
            INSERT INTO news.{category_table}
            (title, link, content, rubric, source, category, published_date)
            VALUES
            (%(title)s, %(link)s, %(content)s, %(rubric)s, %(source)s, %(category)s, %(published_date)s)
            """
            
            try:
                self.client.execute(query_category, data)
            except:
                pass
            
            self.stats['successfully_saved'] += 1
            self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1
            self.seen_links.add(link)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_article(self, title: str, link: str, rubric: str = ""):
        """Обрабатывает одну статью"""
        self.stats['total_found'] += 1
        
        # Проверка дубликата
        if self.is_duplicate_simple(link):
            print(f"⚠️  Дубликат: {title[:60]}...")
            self.stats['duplicates_skipped'] += 1
            return
        
        # Получаем содержимое
        content = self.get_article_content(link)
        if not content:
            print(f"❌ Нет содержимого: {title[:60]}...")
            self.stats['errors'] += 1
            return
        
        # Предобработка
        clean_title, clean_content = preprocessor.preprocess_article(title, content)
        
        # Классификация
        category, confidence, scores = classifier.classify(clean_title, clean_content)
        
        if category is None or confidence < 2.0:
            # Если не удалось классифицировать, пропускаем статью
            print(f"⚠️  Низкая релевантность ({confidence:.2f}): {clean_title[:60]}...")
            self.stats['low_confidence_skipped'] += 1
            return
        
        # Пропускаем статьи с категорией 'other' - они не нужны в БД
        if category == 'other':
            print(f"❌ Пропущено (категория 'other'): {clean_title[:60]}...")
            self.stats['low_confidence_skipped'] += 1
            return
        
        # Сохраняем
        success = self.save_article(clean_title, clean_content, link, category, rubric)
        
        if success:
            print(f"✅ Сохранено [{category}, {confidence:.2f}]: {clean_title[:60]}...")
    
    def parse_main_page(self):
        """Парсит главную страницу"""
        print(f"\n🔍 Парсинг главной страницы Gazeta.ru...")
        
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Находим все ссылки на новости
            articles = soup.find_all('a', href=lambda href: href and '/news/' in href)
            
            print(f"📰 Найдено ссылок /news/: {len(articles)}")
            
            processed = 0
            for article in articles:
                if processed >= 50:  # Ограничение
                    break
                
                try:
                    link = article.get('href', '')
                    
                    # Формируем полный URL
                    if link and not link.startswith('http'):
                        link = f"{self.base_url}{link}"
                    
                    if not link or link == self.base_url or link.endswith('/news/'):
                        continue
                    
                    # Получаем заголовок
                    title = article.get_text(strip=True)
                    
                    # Удаляем время в конце заголовка (формат: "текст20:46")
                    title = re.sub(r'\d{2}:\d{2}$', '', title).strip()
                    
                    if not title or len(title) < 10:
                        continue
                    
                    self.process_article(title, link)
                    processed += 1
                    
                    # Задержка
                    time.sleep(random.uniform(0.3, 0.8))
                    
                except Exception as e:
                    print(f"⚠️  Ошибка обработки: {e}")
                    continue
            
            print(f"\n✓ Обработано {processed} статей")
                    
        except Exception as e:
            print(f"❌ Ошибка загрузки главной: {e}")
            self.stats['errors'] += 1
    
    def parse_politics(self):
        """Парсит раздел политики"""
        print(f"\n🔍 Парсинг раздела политики...")
        
        try:
            url = f"{self.base_url}/politics"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.find_all('a', href=lambda href: href and '/politics/' in href and '/news/' in href)
            
            print(f"📰 Найдено политических новостей: {len(articles)}")
            
            processed = 0
            for article in articles[:30]:
                try:
                    link = article.get('href', '')
                    if link and not link.startswith('http'):
                        link = f"{self.base_url}{link}"
                    
                    if not link or link.endswith('/politics/'):
                        continue
                    
                    title = article.get_text(strip=True)
                    
                    # Удаляем время в конце заголовка
                    title = re.sub(r'\d{2}:\d{2}$', '', title).strip()
                    
                    if not title or len(title) < 10:
                        continue
                    
                    self.process_article(title, link, rubric="Политика")
                    processed += 1
                    
                    time.sleep(random.uniform(0.3, 0.8))
                    
                except Exception as e:
                    continue
            
            print(f"✓ Обработано {processed} политических статей")
                    
        except Exception as e:
            print(f"❌ Ошибка парсинга политики: {e}")
    
    def print_stats(self):
        """Выводит статистику"""
        print("\n" + "=" * 60)
        print(f"📊 СТАТИСТИКА ПАРСИНГА: {self.source_name.upper()}")
        print("=" * 60)
        print(f"🔍 Найдено статей: {self.stats['total_found']}")
        print(f"✅ Успешно сохранено: {self.stats['successfully_saved']}")
        print(f"⚠️  Пропущено дубликатов: {self.stats['duplicates_skipped']}")
        print(f"⚠️  Низкая релевантность: {self.stats['low_confidence_skipped']}")
        print(f"🚫 Ошибок: {self.stats['errors']}")
        
        if self.stats['by_category']:
            print("\n📑 По категориям:")
            for cat, count in sorted(self.stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                print(f"  - {cat}: {count}")
        
        print("=" * 60 + "\n")
    
    def run(self):
        """Запуск парсера"""
        try:
            self.connect_db()
            self.parse_main_page()
            self.parse_politics()
        finally:
            self.close_db()
            self.print_stats()


def main():
    parser = argparse.ArgumentParser(description='Упрощенный парсер Gazeta.ru')
    parser.add_argument('--hours', type=int, default=24, help='Период парсинга в часах')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 GAZETA.RU ПАРСЕР (УПРОЩЕННАЯ ВЕРСИЯ)")
    print("=" * 60)
    print(f"⏰ Период: {args.hours} часов")
    print("=" * 60)
    
    try:
        gazeta_parser = SimpleGazetaParser(parse_period_hours=args.hours)
        gazeta_parser.run()
        print("\n✅ Парсинг завершен!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

