#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование улучшенной системы классификации экстремистского контента
"""

import sys
import os
import json
from datetime import datetime

# Добавляем путь к модулям приложения
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from ai.content_classifier import ExtremistContentClassifier
from test_data.extremism_training_dataset import EXTREMISM_TRAINING_DATASET, get_training_data, get_dataset_stats

def test_classifier_with_dataset():
    """Тестирование классификатора на новом датасете"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СИСТЕМЫ КЛАССИФИКАЦИИ")
    print("=" * 60)
    
    # Инициализация классификатора
    classifier = ExtremistContentClassifier()
    
    # Статистика датасета
    stats = get_dataset_stats()
    print(f"\nСтатистика тестового датасета:")
    print(f"📊 Нормальный контент: {stats['normal']} примеров")
    print(f"⚠️  Подозрительный контент: {stats['suspicious']} примеров")
    print(f"🚨 Экстремистский контент: {stats['extremist']} примеров")
    print(f"📈 Всего примеров: {stats['total']}")
    
    # Результаты тестирования
    results = {
        'normal': {'correct': 0, 'total': 0, 'misclassified': []},
        'suspicious': {'correct': 0, 'total': 0, 'misclassified': []},
        'extremist': {'correct': 0, 'total': 0, 'misclassified': []}
    }
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ КЛАССИФИКАЦИИ")
    print("=" * 60)
    
    # Тестирование каждого типа контента
    for content_type, examples in EXTREMISM_TRAINING_DATASET.items():
        print(f"\n🔍 Тестирование {content_type.upper()} контента:")
        print("-" * 40)
        
        for i, example in enumerate(examples, 1):
            text = example['text']
            expected_classification = example['classification']
            expected_score = example['extremism_score']
            
            # Классификация
            result = classifier.classify_content(text)
            predicted_label = result['label']
            confidence = result['confidence']
            risk_score = result['risk_score']
            keywords = result['keywords']
            
            # Проверка правильности классификации
            is_correct = predicted_label == expected_classification
            results[content_type]['total'] += 1
            
            if is_correct:
                results[content_type]['correct'] += 1
                status = "✅ ПРАВИЛЬНО"
            else:
                results[content_type]['misclassified'].append({
                    'text': text[:100] + "..." if len(text) > 100 else text,
                    'expected': expected_classification,
                    'predicted': predicted_label,
                    'confidence': confidence
                })
                status = "❌ ОШИБКА"
            
            print(f"\nПример {i}: {status}")
            print(f"📝 Текст: {text[:80]}{'...' if len(text) > 80 else ''}")
            print(f"🎯 Ожидалось: {expected_classification}")
            print(f"🤖 Предсказано: {predicted_label} (уверенность: {confidence:.2f})")
            print(f"📊 Риск-скор: {risk_score}")
            if keywords:
                print(f"🔑 Ключевые слова: {', '.join(keywords[:5])}")
            
            # Показываем выделенные экстремистские фразы
            if 'extremist_phrases' in example and example['extremist_phrases']:
                print(f"🚨 Экстремистские фразы: {', '.join(example['extremist_phrases'])}")
    
    # Общая статистика
    print("\n" + "=" * 60)
    print("ОБЩАЯ СТАТИСТИКА ТОЧНОСТИ")
    print("=" * 60)
    
    total_correct = 0
    total_examples = 0
    
    for content_type, result in results.items():
        accuracy = (result['correct'] / result['total']) * 100 if result['total'] > 0 else 0
        total_correct += result['correct']
        total_examples += result['total']
        
        print(f"\n{content_type.upper()}:")
        print(f"  Правильно: {result['correct']}/{result['total']} ({accuracy:.1f}%)")
        
        if result['misclassified']:
            print(f"  Ошибки классификации:")
            for error in result['misclassified']:
                print(f"    - Ожидалось '{error['expected']}', получено '{error['predicted']}' ({error['confidence']:.2f})")
    
    overall_accuracy = (total_correct / total_examples) * 100 if total_examples > 0 else 0
    print(f"\n🎯 ОБЩАЯ ТОЧНОСТЬ: {total_correct}/{total_examples} ({overall_accuracy:.1f}%)")
    
    return results

def test_specific_examples():
    """Тестирование на конкретных примерах для демонстрации"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ НА КОНКРЕТНЫХ ПРИМЕРАХ")
    print("=" * 60)
    
    classifier = ExtremistContentClassifier()
    
    test_examples = [
        {
            "text": "Сегодня отличная погода для прогулки в парке!",
            "expected": "normal"
        },
        {
            "text": "Эти политики совсем обнаглели! Пора показать им, кто здесь хозяин!",
            "expected": "suspicious"
        },
        {
            "text": "Смерть врагам народа! Пора взять оружие и уничтожить всех предателей!",
            "expected": "extremist"
        }
    ]
    
    for i, example in enumerate(test_examples, 1):
        print(f"\n--- Пример {i} ---")
        result = classifier.classify_content(example['text'])
        
        print(f"📝 Текст: {example['text']}")
        print(f"🎯 Ожидаемая классификация: {example['expected']}")
        print(f"🤖 Результат: {result['label']} (уверенность: {result['confidence']:.2f})")
        print(f"📊 Риск-скор: {result['risk_score']}")
        
        if result['keywords']:
            print(f"🔑 Найденные ключевые слова: {', '.join(result['keywords'])}")
        
        # Показываем выделенный текст
        if result.get('highlighted_text'):
            print(f"🎨 Выделенный текст: {result['highlighted_text']}")

def save_test_results(results):
    """Сохранение результатов тестирования"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 Результаты сохранены в файл: {filename}")

if __name__ == "__main__":
    try:
        # Основное тестирование
        results = test_classifier_with_dataset()
        
        # Демонстрация на примерах
        test_specific_examples()
        
        # Сохранение результатов
        save_test_results(results)
        
        print("\n" + "=" * 60)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()