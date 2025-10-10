#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки всех парсеров с Gen-API классификатором
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

def test_gen_api_classifier():
    """Тестирует Gen-API классификатор"""
    logger.info("=== Тестирование Gen-API классификатора ===")
    
    # Проверяем наличие API ключа
    api_key = os.environ.get('GEN_API_KEY')
    
    if not api_key:
        logger.error("❌ Не найден API ключ gen-api.ru в переменных окружения")
        logger.info("Установите переменную в файле .env:")
        logger.info("GEN_API_KEY=sk-fFv5kuV9ZZg4wNJuOY1RUGYv5KIf3dMkUeR27VclgRTprL1A04ucEN8lFwzr")
        return False
    
    logger.info(f"API ключ: {api_key[:20]}...")
    
    try:
        # Создаем экземпляр классификатора
        classifier = GenApiNewsClassifier(api_key=api_key)
        
        # Тестовые новости для всех 5 категорий
        test_news = [
            {
                "title": "Военные действия в Украине продолжаются",
                "content": "Сегодня произошли новые боевые столкновения в районе Донецка. По данным Минобороны, наши войска успешно отразили атаку противника.",
                "expected_category": "military_operations"
            },
            {
                "title": "Гуманитарная помощь беженцам",
                "content": "Международные организации доставили гуманитарную помощь в зону конфликта. Помощь включает продукты питания и медицинские принадлежности.",
                "expected_category": "humanitarian_crisis"
            },
            {
                "title": "Экономические санкции против России",
                "content": "Европейский союз ввел новые экономические санкции против России. Это может повлиять на торговые отношения между странами.",
                "expected_category": "economic_consequences"
            },
            {
                "title": "Политические переговоры по Украине",
                "content": "Президенты России и США провели телефонные переговоры по ситуации в Украине. Обсуждались вопросы дипломатического урегулирования конфликта.",
                "expected_category": "political_decisions"
            },
            {
                "title": "Социальные сети и информационная война",
                "content": "В социальных сетях распространяется информация о конфликте. Эксперты отмечают важность проверки фактов и борьбы с дезинформацией.",
                "expected_category": "information_social"
            }
        ]
        
        logger.info(f"\nТестируем классификацию {len(test_news)} новостей...")
        
        success_count = 0
        total_tokens = 0
        
        for i, news in enumerate(test_news, 1):
            logger.info(f"\n--- Новость {i} ---")
            logger.info(f"Заголовок: {news['title']}")
            
            try:
                result = classifier.classify(news['title'], news['content'])
                
                # Проверяем результат
                is_correct = result['category_name'] == news['expected_category']
                if is_correct:
                    success_count += 1
                    logger.info("✅ Классификация корректна!")
                else:
                    logger.warning(f"⚠️ Ожидалось: {news['expected_category']}, получено: {result['category_name']}")
                
                logger.info(f"  Категория: {result['category_name']}")
                logger.info(f"  Индекс напряженности: {result['social_tension_index']}")
                logger.info(f"  Индекс всплеска: {result['spike_index']}")
                logger.info(f"  Уверенность: {result['confidence']:.2f}")
                logger.info(f"  Кэшировано: {result.get('cached', False)}")
                
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
        
        # Итоговая оценка
        accuracy = (success_count / len(test_news)) * 100
        logger.info(f"\n=== ИТОГОВАЯ ОЦЕНКА ===")
        logger.info(f"Точность классификации: {accuracy:.1f}% ({success_count}/{len(test_news)})")
        
        if accuracy >= 80:
            logger.info("🎉 Классификатор работает отлично!")
            return True
        elif accuracy >= 60:
            logger.info("✅ Классификатор работает хорошо")
            return True
        else:
            logger.warning("⚠️ Классификатор требует улучшения")
            return False
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании классификатора: {e}")
        return False

def test_base_parser():
    """Тестирует базовый парсер с Gen-API классификатором"""
    logger.info("\n=== Тестирование BaseNewsParser с Gen-API ===")
    
    try:
        from parsers.base_parser import BaseNewsParser
        
        # Создаем тестовый парсер
        parser = BaseNewsParser(
            source_name="test_source",
            base_url="https://example.com",
            enable_classification=True,
            enable_duplicate_check=False,  # Отключаем для теста
            enable_preprocessing=True
        )
        
        # Тестовая статья
        test_title = "Тестовая новость о военных действиях"
        test_content = "Это тестовая новость для проверки работы базового парсера с Gen-API классификатором."
        
        logger.info(f"Тестируем статью: {test_title}")
        
        # Тестируем классификацию
        category, confidence, scores = parser.classify_article(test_title, test_content)
        
        if category:
            logger.info(f"✅ Классификация успешна!")
            logger.info(f"  Категория: {category}")
            logger.info(f"  Уверенность: {confidence:.2f}")
            logger.info(f"  Индексы: {scores}")
            return True
        else:
            logger.warning("⚠️ Классификация не удалась")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании BaseNewsParser: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("=== ТЕСТИРОВАНИЕ ВСЕХ ПАРСЕРОВ С GEN-API ===")
    
    # Тестируем Gen-API классификатор
    classifier_ok = test_gen_api_classifier()
    
    # Тестируем базовый парсер
    parser_ok = test_base_parser()
    
    # Итоговый результат
    logger.info("\n" + "=" * 60)
    logger.info("ИТОГОВЫЙ РЕЗУЛЬТАТ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60)
    
    if classifier_ok and parser_ok:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        logger.info("Gen-API классификатор готов к использованию во всех парсерах")
    else:
        logger.warning("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        if not classifier_ok:
            logger.warning("- Проблемы с Gen-API классификатором")
        if not parser_ok:
            logger.warning("- Проблемы с BaseNewsParser")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
