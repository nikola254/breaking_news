#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный парсер новостей с сайта Gazeta.ru
С предобработкой, классификацией и проверкой дубликатов
"""
import sys
import os
from datetime import datetime
import time
import random
import argparse

# Добавляем пути
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsers.base_parser import BaseNewsParser
from bs4 import BeautifulSoup


class GazetaParser(BaseNewsParser):
    """Парсер для Gazeta.ru"""
    
    def __init__(self, parse_period_hours: int = 24):
        super().__init__(
            source_name='gazeta',
            base_url='https://www.gazeta.ru',
            parse_period_hours=parse_period_hours,
            enable_duplicate_check=True,
            enable_classification=True,
            enable_preprocessing=True,
            min_confidence=0.15
        )
    
    def get_article_content(self, url: str) -> str:
        """
        Извлекает полное содержимое статьи с Gazeta.ru
        
        Args:
            url: URL статьи
            
        Returns:
            Текст статьи
        """
        html = self.fetch_url(url)
        if not html:
            return ""
        
        soup = self.parse_html(html)
        
        # Поиск основного содержимого
        article_body = soup.find("div", class_="b_article-text")
        
        if not article_body:
            article_body = soup.find("div", class_="article_text")
        
        if not article_body:
            article_body = soup.find("div", {"itemprop": "articleBody"})
        
        if not article_body:
            return "Содержимое статьи недоступно"
        
        # Извлекаем параграфы
        paragraphs = article_body.find_all("p")
        
        content = "\n\n".join([
            p.get_text(strip=True)
            for p in paragraphs
            if p.get_text(strip=True) and len(p.get_text(strip=True)) > 10
        ])
        
        return content[:5000]
    
    def parse_main_page(self):
        """Парсит главную страницу Gazeta.ru"""
        print(f"\n🔍 Начинаем парсинг Gazeta.ru (период: {self.parse_period_hours} часов)...")
        
        html = self.fetch_url(self.base_url)
        if not html:
            print("❌ Не удалось загрузить главную страницу")
            return
        
        soup = self.parse_html(html)
        
        # Находим все ссылки на новости
        articles = soup.find_all("a", class_="headline_main")
        
        if not articles:
            articles = soup.find_all("div", class_="b_ear-inner")
        
        print(f"📰 Найдено статей на главной: {len(articles)}")
        
        for article in articles:
            try:
                if article.name == 'a':
                    link = article.get('href', '')
                    title = article.get_text(strip=True)
                else:
                    link_elem = article.find('a')
                    if not link_elem:
                        continue
                    link = link_elem.get('href', '')
                    title = link_elem.get_text(strip=True)
                
                # Формируем полный URL
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                if not link or not title or link == self.base_url:
                    continue
                
                # Получаем содержимое
                content = self.get_article_content(link)
                
                # Обрабатываем статью
                self.process_article(
                    title=title,
                    content=content,
                    link=link,
                    rubric="",
                    published_date=datetime.now()
                )
                
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"⚠️  Ошибка обработки статьи: {e}")
                self.stats['errors'] += 1
                continue
    
    def parse_politics(self):
        """Парсит раздел политики"""
        print("\n📂 Парсинг раздела: Политика")
        
        url = f"{self.base_url}/politics"
        html = self.fetch_url(url)
        
        if not html:
            return
        
        soup = self.parse_html(html)
        articles = soup.find_all("div", class_="b_ear-inner")[:30]
        
        print(f"📰 Найдено статей: {len(articles)}")
        
        for article in articles:
            try:
                link_elem = article.find("a")
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                link = link_elem.get('href', '')
                
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                if not link or not title:
                    continue
                
                content = self.get_article_content(link)
                
                self.process_article(
                    title=title,
                    content=content,
                    link=link,
                    rubric="Политика",
                    published_date=datetime.now()
                )
                
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"⚠️  Ошибка: {e}")
                continue
    
    def parse_news(self):
        """Парсит раздел новостей"""
        print("\n📂 Парсинг раздела: Новости")
        
        url = f"{self.base_url}/news"
        html = self.fetch_url(url)
        
        if not html:
            return
        
        soup = self.parse_html(html)
        articles = soup.find_all("a", class_="headline")[:30]
        
        print(f"📰 Найдено статей: {len(articles)}")
        
        for article in articles:
            try:
                title = article.get_text(strip=True)
                link = article.get('href', '')
                
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                if not link or not title:
                    continue
                
                content = self.get_article_content(link)
                
                self.process_article(
                    title=title,
                    content=content,
                    link=link,
                    rubric="Новости",
                    published_date=datetime.now()
                )
                
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"⚠️  Ошибка: {e}")
                continue
    
    def parse(self):
        """Основной метод парсинга"""
        self.parse_main_page()
        self.parse_politics()
        self.parse_news()


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Парсер Gazeta.ru с улучшенной обработкой')
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Период парсинга в часах (по умолчанию: 24)'
    )
    parser.add_argument(
        '--no-duplicates-check',
        action='store_true',
        help='Отключить проверку дубликатов'
    )
    parser.add_argument(
        '--no-classification',
        action='store_true',
        help='Отключить классификацию'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 GAZETA.RU ПАРСЕР (УЛУЧШЕННАЯ ВЕРСИЯ)")
    print("=" * 60)
    print(f"⏰ Период парсинга: {args.hours} часов")
    print(f"🔍 Проверка дубликатов: {'ВКЛ' if not args.no_duplicates_check else 'ВЫКЛ'}")
    print(f"🤖 Классификация: {'ВКЛ' if not args.no_classification else 'ВЫКЛ'}")
    print("=" * 60)
    
    try:
        with GazetaParser(parse_period_hours=args.hours) as gazeta_parser:
            if args.no_duplicates_check:
                gazeta_parser.enable_duplicate_check = False
            if args.no_classification:
                gazeta_parser.enable_classification = False
            
            gazeta_parser.parse()
        
        print("\n✅ Парсинг завершен успешно!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Парсинг прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

