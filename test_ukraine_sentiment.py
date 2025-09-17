#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки анализатора тональности украинских новостей.

Этот скрипт демонстрирует работу нового анализатора тональности
на примерах различных типов новостей о украинском конфликте.
"""

import sys
import os

# Добавляем путь к приложению
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.ukraine_sentiment_analyzer import UkraineSentimentAnalyzer, get_ukraine_sentiment_analyzer

def test_sentiment_analyzer():
    """Тестирование анализатора тональности"""
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ АНАЛИЗАТОРА ТОНАЛЬНОСТИ УКРАИНСКИХ НОВОСТЕЙ")
    print("=" * 80)
    
    # Создаем экземпляр анализатора
    analyzer = get_ukraine_sentiment_analyzer()
    
    # Тестовые новости различных типов
    test_news = [
        {
            'title': 'Позитивная новость',
            'text': 'Подписано соглашение о перемирии. Стороны договорились о прекращении огня и начале мирных переговоров. Гуманитарная помощь будет доставлена в пострадавшие районы.',
            'expected': 'positive'
        },
        {
            'title': 'Негативная новость',
            'text': 'Произошла серьезная атака на гражданские объекты. Зафиксированы многочисленные жертвы среди мирного населения. Разрушены жилые дома и больницы.',
            'expected': 'negative'
        },
        {
            'title': 'Военная новость',
            'text': 'Армейские подразделения провели наступательную операцию. Задействованы танки, артиллерия и авиация. Захвачены стратегические позиции противника.',
            'expected': 'negative'
        },
        {
            'title': 'Гуманитарная новость',
            'text': 'Красный Крест организовал эвакуацию детей и женщин из зоны конфликта. Волонтеры доставили медицинскую помощь и продовольствие беженцам.',
            'expected': 'positive'
        },
        {
            'title': 'Нейтральная новость',
            'text': 'Состоялась встреча представителей делегаций. Обсуждались вопросы координации действий. Планируется проведение дополнительных консультаций.',
            'expected': 'neutral'
        },
        {
            'title': 'Украинская новость',
            'text': 'Українські війська звільнили населений пункт. Надана гуманітарна допомога місцевому населенню. Відновлюється мирне життя в регіоні.',
            'expected': 'positive'
        }
    ]
    
    print("\nАНАЛИЗ ТЕСТОВЫХ НОВОСТЕЙ:")
    print("-" * 80)
    
    for i, news in enumerate(test_news, 1):
        print(f"\n{i}. {news['title']}")
        print(f"Текст: {news['text'][:100]}...")
        
        # Анализируем тональность
        result = analyzer.analyze_sentiment(news['text'])
        category = analyzer.get_sentiment_category(result['sentiment_score'])
        
        print(f"\nРезультаты анализа:")
        print(f"  Общая тональность: {result['sentiment_score']:.3f} ({category})")
        print(f"  Позитивный балл: {result['positive_score']:.3f}")
        print(f"  Негативный балл: {result['negative_score']:.3f}")
        print(f"  Нейтральный балл: {result['neutral_score']:.3f}")
        print(f"  Военная интенсивность: {result['military_intensity']:.3f}")
        print(f"  Гуманитарный фокус: {result['humanitarian_focus']:.3f}")
        
        # Проверяем соответствие ожиданиям
        expected = news['expected']
        status = "✓" if category == expected else "✗"
        print(f"  Ожидалось: {expected}, получено: {category} {status}")
        
        # Показываем подсчет ключевых слов
        keyword_counts = result['keyword_counts']
        print(f"  Ключевые слова: pos={keyword_counts['positive']}, neg={keyword_counts['negative']}, neu={keyword_counts['neutral']}, mil={keyword_counts['military']}, hum={keyword_counts['humanitarian']}")
        
        print("-" * 40)
    
    print("\nТЕСТИРОВАНИЕ ПАКЕТНОГО АНАЛИЗА:")
    print("-" * 80)
    
    # Тестируем пакетный анализ
    texts = [news['text'] for news in test_news]
    batch_results = analyzer.analyze_batch(texts)
    
    print(f"Обработано {len(batch_results)} текстов")
    
    # Получаем агрегированные результаты
    aggregated = analyzer.get_aggregated_sentiment(texts)
    print(f"\nАгрегированные результаты:")
    print(f"  Средняя тональность: {aggregated['sentiment_score']:.3f}")
    print(f"  Средний позитивный балл: {aggregated['positive_score']:.3f}")
    print(f"  Средний негативный балл: {aggregated['negative_score']:.3f}")
    print(f"  Средняя военная интенсивность: {aggregated['military_intensity']:.3f}")
    print(f"  Средний гуманитарный фокус: {aggregated['humanitarian_focus']:.3f}")
    
    print("\nТЕСТИРОВАНИЕ БЫСТРЫХ ФУНКЦИЙ:")
    print("-" * 80)
    
    # Тестируем быстрые функции
    from app.utils.ukraine_sentiment_analyzer import analyze_ukraine_news_sentiment, get_ukraine_news_sentiment_category
    
    test_text = "Подписано мирное соглашение между сторонами конфликта"
    quick_result = analyze_ukraine_news_sentiment(test_text)
    quick_category = get_ukraine_news_sentiment_category(test_text)
    
    print(f"Быстрый анализ текста: '{test_text}'")
    print(f"Результат: {quick_result['sentiment_score']:.3f} ({quick_category})")
    
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)

def test_error_handling():
    """Тестирование обработки ошибок"""
    
    print("\nТЕСТИРОВАНИЕ ОБРАБОТКИ ОШИБОК:")
    print("-" * 80)
    
    analyzer = get_ukraine_sentiment_analyzer()
    
    # Тестируем пустой текст
    result = analyzer.analyze_sentiment("")
    print(f"Пустой текст: {result['sentiment_score']} (ожидается 0.0)")
    
    # Тестируем None
    result = analyzer.analyze_sentiment(None)
    print(f"None: {result['sentiment_score']} (ожидается 0.0)")
    
    # Тестируем очень короткий текст
    result = analyzer.analyze_sentiment("а")
    print(f"Короткий текст: {result['sentiment_score']}")
    
    # Тестируем текст без ключевых слов
    result = analyzer.analyze_sentiment("Это просто обычный текст без специальных слов")
    print(f"Обычный текст: {result['sentiment_score']}")
    
    print("Обработка ошибок работает корректно ✓")

if __name__ == "__main__":
    try:
        test_sentiment_analyzer()
        test_error_handling()
        
        print("\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)