#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный парсер новостей с сайта Lenta.ru
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


class LentaParser(BaseNewsParser):
    """Парсер для Lenta.ru"""
    
    def __init__(self, parse_period_hours: int = 24):
        super().__init__(
            source_name='lenta',
            base_url='https://lenta.ru',
            parse_period_hours=parse_period_hours,
            enable_duplicate_check=True,
            enable_classification=True,
            enable_preprocessing=True,
            min_confidence=0.15
        )
    
    def get_article_content(self, url: str) -> str:
        """
        Извлекает полное содержимое статьи с Lenta.ru
        
        Args:
            url: URL статьи
            
        Returns:
            Текст статьи
        """
        html = self.fetch_url(url)
        if not html:
            return ""
        
        soup = self.parse_html(html)
        
        # Поиск основного содержимого статьи
        article_body = soup.find("div", class_="topic-body__content")
        
        if not article_body:
            # Альтернативные селекторы
            article_body = soup.find("div", class_="b-text")
        
        if not article_body:
            article_body = soup.find("div", class_="js-topic__text")
        
        if not article_body:
            return "Содержимое статьи недоступно"
        
        # Извлекаем параграфы
        paragraphs = article_body.find_all(
            ["p", "div"],
            class_=lambda x: x != "topic-header"
        )
        
        content = "\n\n".join([
            p.get_text(strip=True)
            for p in paragraphs
            if p.get_text(strip=True)
        ])
        
        return content[:5000]  # Ограничиваем размер
    
    def parse_main_page(self):
        """Парсит главную страницу Lenta.ru"""
        print(f"\n🔍 Начинаем парсинг Lenta.ru (период: {self.parse_period_hours} часов)...")
        
        html = self.fetch_url(self.base_url)
        if not html:
            print("❌ Не удалось загрузить главную страницу")
            return
        
        soup = self.parse_html(html)
        
        # Находим все ссылки на статьи
        articles = soup.find_all("a", class_="card-full-news")
        
        if not articles:
            # Альтернативный селектор
            articles = soup.find_all("a", class_="card-mini")
        
        print(f"📰 Найдено статей на главной: {len(articles)}")
        
        cutoff_date = self.get_cutoff_date()
        
        for article in articles:
            try:
                # Извлекаем данные
                title_elem = article.find("span", class_="card-full-news__title")
                if not title_elem:
                    title_elem = article.find("h3")
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = article.get('href', '')
                
                # Формируем полный URL
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                # Пропускаем пустые ссылки
                if not link or link == self.base_url:
                    continue
                
                # Получаем содержимое статьи
                content = self.get_article_content(link)
                
                # Извлекаем рубрику (если есть)
                rubric_elem = article.find("span", class_="card-full-news__rubric")
                rubric = rubric_elem.get_text(strip=True) if rubric_elem else ""
                
                # Обрабатываем статью
                self.process_article(
                    title=title,
                    content=content,
                    link=link,
                    rubric=rubric,
                    published_date=datetime.now()
                )
                
                # Задержка между запросами
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"⚠️  Ошибка обработки статьи: {e}")
                self.stats['errors'] += 1
                continue
    
    def parse_rubric(self, rubric_url: str, rubric_name: str):
        """
        Парсит определенную рубрику
        
        Args:
            rubric_url: URL рубрики
            rubric_name: Название рубрики
        """
        print(f"\n📂 Парсинг рубрики: {rubric_name}")
        
        html = self.fetch_url(rubric_url)
        if not html:
            return
        
        soup = self.parse_html(html)
        
        # Находим статьи в рубрике
        articles = soup.find_all("li", class_="archive-page__item")
        
        print(f"📰 Найдено статей в рубрике: {len(articles)}")
        
        for article in articles[:50]:  # Ограничиваем количество
            try:
                link_elem = article.find("a")
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                link = link_elem.get('href', '')
                
                if link and not link.startswith('http'):
                    link = f"{self.base_url}{link}"
                
                if not link:
                    continue
                
                # Получаем содержимое
                content = self.get_article_content(link)
                
                # Обрабатываем
                self.process_article(
                    title=title,
                    content=content,
                    link=link,
                    rubric=rubric_name,
                    published_date=datetime.now()
                )
                
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"⚠️  Ошибка: {e}")
                continue
    
    def parse(self):
        """Основной метод парсинга"""
        # Парсим главную страницу
        self.parse_main_page()
        
        # Парсим важные рубрики
        important_rubrics = [
            ('https://lenta.ru/rubrics/world/', 'Мир'),
            ('https://lenta.ru/rubrics/russia/', 'Россия'),
            ('https://lenta.ru/rubrics/economics/', 'Экономика'),
        ]
        
        for rubric_url, rubric_name in important_rubrics:
            self.parse_rubric(rubric_url, rubric_name)
            time.sleep(random.uniform(1, 2))


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Парсер Lenta.ru с улучшенной обработкой')
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
    print("🚀 LENTA.RU ПАРСЕР (УЛУЧШЕННАЯ ВЕРСИЯ)")
    print("=" * 60)
    print(f"⏰ Период парсинга: {args.hours} часов")
    print(f"🔍 Проверка дубликатов: {'ВКЛ' if not args.no_duplicates_check else 'ВЫКЛ'}")
    print(f"🤖 Классификация: {'ВКЛ' if not args.no_classification else 'ВЫКЛ'}")
    print("=" * 60)
    
    try:
        with LentaParser(parse_period_hours=args.hours) as lenta_parser:
            # Настраиваем опции
            if args.no_duplicates_check:
                lenta_parser.enable_duplicate_check = False
            if args.no_classification:
                lenta_parser.enable_classification = False
            
            # Запускаем парсинг
            lenta_parser.parse()
        
        print("\n✅ Парсинг завершен успешно!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Парсинг прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

