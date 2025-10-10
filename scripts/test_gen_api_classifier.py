#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки gen-api.ru классификатора
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsers.gen_api_classifier import GenApiNewsClassifier

# Загружаем переменные окружения
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_classifier():
    """Тестирует работу классификатора"""
    logger.info("=== Тестирование gen-api.ru классификатора ===")
    
    # Проверяем наличие API ключа
    api_key = os.environ.get('GEN_API_KEY')
    
    if not api_key:
        logger.error("❌ Не найден API ключ gen-api.ru в переменных окружения")
        logger.info("Установите переменную в файле .env:")
        logger.info("GEN_API_KEY=sk-fFv5kuV9ZZg4wNJuOY1RUGYv5KIf3dMkUeR27VclgRTprL1A04ucEN8lFwzr")
        return
    
    logger.info(f"API ключ: {api_key[:20]}...")
    
    try:
        # Создаем экземпляр классификатора
        classifier = GenApiNewsClassifier(api_key=api_key)
        
        # Тестовые новости
        test_news = [
            {
                "title": "Военные действия в Украине продолжаются",
                "content": "Сегодня произошли новые боевые столкновения в районе Донецка. По данным Минобороны, наши войска успешно отразили атаку противника."
            },
            {
                "title": "Экономические санкции против России",
                "content": "Европейский союз ввел новые экономические санкции против России. Это может повлиять на торговые отношения между странами."
            },
            {
                "title": "Гуманитарная помощь беженцам",
                "content": "Международные организации доставили гуманитарную помощь в зону конфликта. Помощь включает продукты питания и медицинские принадлежности."
            }
        ]
        
        logger.info(f"\nТестируем классификацию {len(test_news)} новостей...")
        
        for i, news in enumerate(test_news, 1):
            logger.info(f"\n--- Новость {i} ---")
            logger.info(f"Заголовок: {news['title']}")
            
            try:
                result = classifier.classify(news['title'], news['content'])
                
                logger.info(f"✅ Результат классификации:")
                logger.info(f"  Категория: {result['category_name']}")
                logger.info(f"  Индекс напряженности: {result['social_tension_index']}")
                logger.info(f"  Индекс всплеска: {result['spike_index']}")
                logger.info(f"  Уверенность: {result['confidence']:.2f}")
                logger.info(f"  Кэшировано: {result.get('cached', False)}")
                logger.info(f"  Объяснение: {result.get('reasoning', 'Нет объяснения')}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при классификации новости {i}: {e}")
        
        # Получаем статистику
        stats = classifier.get_stats()
        logger.info(f"\n=== Статистика использования ===")
        logger.info(f"Всего запросов: {stats['total_requests']}")
        logger.info(f"Из кэша: {stats['cached_requests']}")
        logger.info(f"API запросов: {stats['api_requests']}")
        logger.info(f"Использовано токенов: {stats['tokens_used']}")
        logger.info(f"Ошибок: {stats['errors']}")
        
        logger.info("\n🎉 Тест завершен! Классификатор работает.")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании классификатора: {e}")

def test_api_connection():
    """Тестирует подключение к API"""
    logger.info("=== Тестирование подключения к gen-api.ru ===")
    
    api_key = os.environ.get('GEN_API_KEY')
    
    if not api_key:
        logger.error("❌ Не найден API ключ")
        return
    
    try:
        import requests
        
        # Простой тест подключения
        url = "https://api.gen-api.ru/api/v1/networks/chat-gpt-3"
        
        test_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Привет! Это тест подключения."
                }
            ],
            "is_sync": False,
            "max_tokens": 50
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        logger.info("Отправляем тестовый запрос...")
        response = requests.post(url, json=test_data, headers=headers, timeout=30)
        
        logger.info(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ Подключение к API успешно!")
            logger.info(f"Request ID: {result.get('request_id')}")
            logger.info(f"Статус: {result.get('status')}")
        else:
            logger.error(f"❌ Ошибка подключения: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании подключения: {e}")

def main():
    """Основная функция"""
    logger.info("=== Тестирование gen-api.ru классификатора ===")
    
    # Тестируем подключение
    test_api_connection()
    
    # Тестируем классификатор
    test_classifier()

if __name__ == "__main__":
    main()
