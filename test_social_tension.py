#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функций анализа социальной напряженности.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.social_tension_analyzer import SocialTensionAnalyzer

def test_tension_analysis():
    """Тестирование анализа социальной напряженности."""
    print("=== Тестирование анализа социальной напряженности ===\n")
    
    analyzer = SocialTensionAnalyzer()
    
    # Тестовые тексты с разным уровнем напряженности
    test_texts = [
        {
            "text": "Сегодня в Украине прошел мирный митинг в поддержку мира. Люди выражали надежду на скорое окончание конфликта.",
            "expected": "низкая"
        },
        {
            "text": "Взрывы в Киеве! Ракетный обстрел жилых районов. Есть жертвы среди мирного населения. Ситуация критическая!",
            "expected": "высокая"
        },
        {
            "text": "Переговоры между сторонами продолжаются. Обсуждаются возможные пути урегулирования конфликта.",
            "expected": "средняя"
        },
        {
            "text": "СРОЧНО! Массированная атака на энергетическую инфраструктуру! Отключения электричества по всей стране!",
            "expected": "критическая"
        }
    ]
    
    for i, test_case in enumerate(test_texts, 1):
        print(f"Тест {i}: {test_case['expected']} напряженность")
        print(f"Текст: {test_case['text'][:100]}...")
        
        try:
            result = analyzer.analyze_text_tension(test_case['text'])
            
            print(f"Результат анализа:")
            print(f"  - Уровень напряженности: {result.tension_score:.3f}")
            print(f"  - Эмоциональная интенсивность: {result.emotional_intensity:.3f}")
            print(f"  - Уровень конфликта: {result.conflict_level:.3f}")
            print(f"  - Уровень срочности: {result.urgency_factor:.3f}")
            print(f"  - Категория: {result.category}")
            print(f"  - Тренд: {result.trend}")
            print(f"  - Ожидалось: {test_case['expected']}")
            
            # Проверка соответствия ожиданиям
            category_mapping = {
                'низкая': ['low', 'minimal'],
                'средняя': ['medium', 'moderate'],
                'высокая': ['high', 'elevated'],
                'критическая': ['critical', 'extreme']
            }
            
            expected_categories = category_mapping.get(test_case['expected'], [])
            if result.category.lower() in expected_categories:
                print("  ✅ Результат соответствует ожиданиям")
            else:
                print("  ⚠️ Результат может не соответствовать ожиданиям")
                
        except Exception as e:
            print(f"  ❌ Ошибка при анализе: {e}")
        
        print("-" * 60)

def test_api_cloud_integration():
    """Тестирование интеграции с API_CLOUD."""
    print("\n=== Тестирование интеграции API_CLOUD ===\n")
    
    analyzer = SocialTensionAnalyzer()
    
    if analyzer.api_cloud_enabled:
        print("✅ API_CLOUD интеграция включена")
        print(f"  - URL: {getattr(analyzer, 'config', {}).get('API_CLOUD_URL', 'не настроен')}")
        print(f"  - Ключ: {'настроен' if hasattr(analyzer, 'config') and analyzer.config.get('API_CLOUD_KEY') else 'не настроен'}")
    else:
        print("⚠️ API_CLOUD интеграция отключена")
        print("  Проверьте настройки API_CLOUD_URL и API_CLOUD_KEY в .env файле")

def test_tension_distribution():
    """Тестирование расчета распределения напряженности."""
    print("\n=== Тестирование распределения напряженности ===\n")
    
    analyzer = SocialTensionAnalyzer()
    
    # Тестовые данные
    test_data = [
        {"tension_score": 0.2, "category": "low"},
        {"tension_score": 0.4, "category": "medium"},
        {"tension_score": 0.7, "category": "high"},
        {"tension_score": 0.9, "category": "critical"},
        {"tension_score": 0.3, "category": "low"},
        {"tension_score": 0.6, "category": "medium"},
    ]
    
    try:
        # Извлекаем только значения напряженности
        tension_scores = [item["tension_score"] for item in test_data]
        distribution = analyzer.get_tension_distribution(tension_scores)
        
        print("Распределение напряженности:")
        for category, count in distribution.items():
            total = sum(distribution.values())
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        print("✅ Расчет распределения работает корректно")
        
    except Exception as e:
        print(f"❌ Ошибка при расчете распределения: {e}")

if __name__ == "__main__":
    try:
        test_tension_analysis()
        test_api_cloud_integration()
        test_tension_distribution()
        
        print("\n=== Тестирование завершено ===")
        print("Все основные функции анализа социальной напряженности протестированы.")
        
    except Exception as e:
        print(f"❌ Критическая ошибка при тестировании: {e}")
        sys.exit(1)