#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ai.content_classifier import ExtremistContentClassifier

def test_classifier():
    classifier = ExtremistContentClassifier()
    
    # Тестовые тексты
    test_texts = [
        "Привет! Как дела? Хорошая погода сегодня.",
        "Покажи мне, как работает эта программа.",
        "Хозяин дома вернулся с работы.",
        "Сегодня отличный день для прогулки!",
        "Нужно показать результаты работы.",
        "Террористическая угроза должна быть устранена",
        "Призываю к насилию против всех врагов",
        "Взрывчатые вещества можно изготовить дома"
    ]
    
    print("=== ТЕСТИРОВАНИЕ УЛУЧШЕННОГО КЛАССИФИКАТОРА ===\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Тест {i}: {text}")
        print("-" * 50)
        
        # Анализ текста
        result = classifier.classify_content(text)
        
        print(f"Классификация: {result.get('label', 'unknown')}")
        print(f"Уверенность: {result.get('confidence', 0):.2f}")
        print(f"Риск-скор: {result.get('risk_score', 0):.2f}")
        
        # Показываем найденные ключевые слова
        if result.get('keywords'):
            print(f"Найденные ключевые слова: {result['keywords']}")
        else:
            print("Ключевые слова не найдены")
        
        # Показываем факторы риска
        if 'rule_based_result' in result and 'risk_factors' in result['rule_based_result']:
            risk_factors = result['rule_based_result']['risk_factors']
            if risk_factors:
                print(f"Факторы риска: {risk_factors}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_classifier()