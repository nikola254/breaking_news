#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный парсер новостей с сайта RBC.ru
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


class RBCParser(BaseNewsParser):
    """Парсер для RBC.ru"""
    
    def __init__(self, parse_period_hours: int = 24):
        super().__init__(
            source_name='rbc',
            base_url='https://www.rbc.ru',
            parse_period_hours=parse_period_hours,
            enable_duplicate_check=True,
            enable_classification=True,
            enable_preprocessing=True,
            min_confidence=0.15
        )
    
    def get_article_content(self, url: str) -> str:
        """
        Извлекает полное содержимое статьи с RBC.ru
        
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
        article_body = soup.find("div", class_="article__text")
        
        if not article_body:
            article_body = soup.find("div", class_="article__content")
        
        if not article_body:
            article_body = soup.find("div", {"itemprop": "articleBody"})
        
        if not article_body:
            return "Содержимое статьи недоступно"
        
        # Извлекаем параграфы
        paragraphs = article_body.find_all("p")
        
        content = "\n\n".join([
            p.get_text(strip=True)
            for p in paragraphs
            if p.get_text(strip=True)
        ])
        
        return content[:5000]
    
    def parse_main_page(self):
        """Парсит главную страницу RBC.ru"""
        print(f"\n🔍 Начинаем парсинг RBC.ru (период: {self.parse_period_hours} часов)...")
        
        html = self.fetch_url(self.base_url)
        if not html:
            print("❌ Не удалось загрузить главную страницу")
            return
        
        soup = self.parse_html(html)
        
        # Находим все ссылки на новости
        articles = soup.find_all("a", class_="news-feed__item")
        
        if not articles:
            articles = soup.find_all("span", class_="news-feed__item")
        
        print(f"📰 Найдено статей на главной: {len(articles)}")
        
        for article in articles:
            try:
                # Получаем ссылку
                if article.name == 'a':
                    link = article.get('href', '')
                else:
                    link_elem = article.find('a')
                    link = link_elem.get('href', '') if link_elem else ''
                
                # Получаем заголовок
                title_elem = article.find("span", class_="news-feed__item__title")
                if not title_elem:
                    title_elem = article.find("div", class_="news-feed__item__title")
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Формируем полный URL
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                if not link or link == self.base_url:
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
        articles = soup.find_all("div", class_="item__wrap")[:30]
        
        print(f"📰 Найдено статей: {len(articles)}")
        
        for article in articles:
            try:
                link_elem = article.find("a", class_="item__link")
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                link = link_elem.get('href', '')
                
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                if not link:
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
    
    def parse(self):
        """Основной метод парсинга"""
        self.parse_main_page()
        self.parse_politics()


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Парсер RBC.ru с улучшенной обработкой')
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
    print("🚀 RBC.RU ПАРСЕР (УЛУЧШЕННАЯ ВЕРСИЯ)")
    print("=" * 60)
    print(f"⏰ Период парсинга: {args.hours} часов")
    print(f"🔍 Проверка дубликатов: {'ВКЛ' if not args.no_duplicates_check else 'ВЫКЛ'}")
    print(f"🤖 Классификация: {'ВКЛ' if not args.no_classification else 'ВЫКЛ'}")
    print("=" * 60)
    
    try:
        with RBCParser(parse_period_hours=args.hours) as rbc_parser:
            if args.no_duplicates_check:
                rbc_parser.enable_duplicate_check = False
            if args.no_classification:
                rbc_parser.enable_classification = False
            
            rbc_parser.parse()
        
        print("\n✅ Парсинг завершен успешно!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Парсинг прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

