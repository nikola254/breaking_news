#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ai.content_classifier import ExtremistContentClassifier

def debug_classifier():
    classifier = ExtremistContentClassifier()
    
    # Тестовые тексты
    test_texts = [
        "Террористическая угроза должна быть устранена",
        "Призываю к насилию против всех врагов",
        "Взрывчатые вещества можно изготовить дома"
    ]
    
    print("=== ОТЛАДКА КЛАССИФИКАТОРА ===\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Тест {i}: {text}")
        print("-" * 50)
        
        # Извлекаем признаки
        features = classifier.extract_features(text)
        print("Извлеченные признаки:")
        for feature, value in features.items():
            if value > 0:
                print(f"  {feature}: {value}")
        
        # Анализ текста
        result = classifier.analyze_text_rule_based(text)
        print(f"\nРиск-скор: {result.get('risk_score', 0)}")
        print(f"Факторы риска: {result.get('risk_factors', [])}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    debug_classifier()