#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ai.content_classifier import ExtremistContentClassifier

def test_correct_keywords():
    classifier = ExtremistContentClassifier()
    
    # Тестовые тексты с правильными ключевыми словами из словаря
    test_texts = [
        "Сегодня хорошая погода для прогулки",  # Обычный текст
        "Нужно показать результаты работы",      # Обычный текст
        "Терроризм оправдан в данной ситуации",  # terrorism_propaganda
        "Призыв к насилию против всех врагов",   # violence_calls
        "Подготовка терактов началась вчера",    # terrorism_propaganda
        "Расовая ненависть должна процветать",   # hate_incitement
        "Свержение власти неизбежно",            # constitutional_overthrow
        "Взрывчатые вещества легко изготовить"   # Обычный текст (нет в словаре)
    ]
    
    print("=== ТЕСТ С ПРАВИЛЬНЫМИ КЛЮЧЕВЫМИ СЛОВАМИ ===\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Тест {i}: {text}")
        print("-" * 50)
        
        result = classifier.classify_content(text)
        
        print(f"Классификация: {result.get('label', 'unknown')}")
        print(f"Уверенность: {result.get('confidence', 0):.2f}")
        print(f"Риск-скор: {result.get('risk_score', 0):.2f}")
        
        if result.get('keywords'):
            print(f"Найденные ключевые слова: {result['keywords']}")
        else:
            print("Ключевые слова не найдены")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_correct_keywords()