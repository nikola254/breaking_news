#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsers.base_parser import BaseNewsParser
from parsers.content_validator import ContentValidator
from parsers.gpt_classifier import GPTNewsClassifier
from parsers.tension_calculator import TensionCalculator
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TestRiaParser(BaseNewsParser):
    """Тестовый парсер РИА Новости с новой системой классификации"""
    
    def __init__(self):
        super().__init__("РИА Новости", "https://ria.ru")
        self.content_validator = ContentValidator()
        self.ai_classifier = GPTNewsClassifier()
        self.tension_calculator = TensionCalculator()
        
    def get_articles(self):
        """Получает статьи с сайта РИА Новости"""
        url = "https://ria.ru/world/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            logger.info(f"Получаем статьи с {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("div", class_="list-item__content")
            
            logger.info(f"Найдено {len(articles)} статей")
            
            articles_data = []
            for article in articles[:5]:  # Берем только первые 5 статей для теста
                try:
                    # Извлекаем заголовок и ссылку
                    link_tag = article.find("a", class_="list-item__title color-font-hover-only")
                    if not link_tag:
                        continue
                    
                    title = link_tag.get_text(strip=True)
                    link = link_tag.get("href")
                    
                    if not link.startswith("http"):
                        link = self.base_url + link
                    
                    # Получаем содержимое статьи
                    content = self._get_article_content(link)
                    
                    if content and len(content) > 100:  # Минимальная длина контента
                        articles_data.append({
                            'title': title,
                            'content': content,
                            'link': link,
                            'published_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        logger.info(f"Добавлена статья: {title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Ошибка при обработке статьи: {e}")
                    continue
            
            logger.info(f"Успешно обработано {len(articles_data)} статей")
            return articles_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении статей: {e}")
            return []
    
    def _get_article_content(self, url):
        """Получает содержимое статьи по URL"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Ищем основной контент статьи
            content_div = soup.find("div", class_="article__text")
            if not content_div:
                content_div = soup.find("div", class_="article__body")
            
            if content_div:
                # Удаляем скрипты и стили
                for script in content_div(["script", "style"]):
                    script.decompose()
                
                content = content_div.get_text(separator=" ", strip=True)
                return content
            
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка при получении контента статьи {url}: {e}")
            return None
    
    def run(self):
        """Запускает парсинг и обработку статей"""
        logger.info("Запуск тестового парсера РИА Новости")
        
        try:
            # Получаем статьи
            articles = self.get_articles()
            
            if not articles:
                logger.warning("Статьи не найдены")
                return
            
            logger.info(f"Найдено {len(articles)} статей для обработки")
            
            # Обрабатываем каждую статью
            processed_count = 0
            saved_count = 0
            rejected_count = 0
            
            for i, article in enumerate(articles):
                logger.info(f"Обрабатываем статью {i+1}/{len(articles)}: {article['title'][:50]}...")
                
                try:
                    # Валидация контента
                    is_valid, cleaned_title, cleaned_content = self.content_validator.validate_content(
                        article['title'], article['content']
                    )
                    
                    if not is_valid:
                        logger.warning(f"Статья отклонена валидатором: {cleaned_content}")
                        rejected_count += 1
                        continue
                    
                    # AI классификация
                    classification_result = self.ai_classifier.classify(cleaned_title, cleaned_content)
                    
                    # Расчет индексов напряженности
                    from parsers.tension_calculator import calculate_both_indices
                    social_tension, spike_index = calculate_both_indices(
                        classification_result['category_name'],
                        cleaned_title,
                        cleaned_content
                    )
                    
                    # Сохраняем статью (в реальном парсере здесь был бы вызов save_article)
                    logger.info(f"Статья обработана успешно:")
                    logger.info(f"  Категория: {classification_result['category_name']}")
                    logger.info(f"  Напряженность: {social_tension:.1f}")
                    logger.info(f"  Индекс всплеска: {spike_index:.1f}")
                    logger.info(f"  Уверенность: {classification_result['confidence']:.2f}")
                    logger.info(f"  Из кэша: {classification_result['cached']}")
                    
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке статьи: {e}")
                    rejected_count += 1
                
                processed_count += 1
            
            logger.info(f"Парсинг завершен:")
            logger.info(f"  Обработано: {processed_count}")
            logger.info(f"  Сохранено: {saved_count}")
            logger.info(f"  Отклонено: {rejected_count}")
            
        except Exception as e:
            logger.error(f"Ошибка в парсере: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Основная функция"""
    # Устанавливаем учетные данные GigaChat (замените на реальные)
    os.environ['GIGACHAT_KEY_ID'] = 'your_key_id_here'
    os.environ['GIGACHAT_SECRET'] = 'your_secret_here'
    os.environ['GIGACHAT_PROJECT_ID'] = 'your_project_id_here'
    
    parser = TestRiaParser()
    parser.run()

if __name__ == "__main__":
    main()
