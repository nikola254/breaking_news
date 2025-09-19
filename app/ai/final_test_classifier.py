#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ai.content_classifier import ExtremistContentClassifier

def final_test():
    classifier = ExtremistContentClassifier()
    
    # Тестовые тексты - обычные и экстремистские
    test_texts = [
        # Обычные тексты
        ("Сегодня хорошая погода для прогулки", "normal"),
        ("Нужно показать результаты работы", "normal"),
        ("Завтра будет важная встреча", "normal"),
        ("Изучаем новые технологии программирования", "normal"),
        
        # Экстремистские тексты с правильными ключевыми словами
        ("Терроризм оправдан в данной ситуации", "extremist"),
        ("Призыв к насилию против всех врагов", "extremist"),
        ("Подготовка терактов началась вчера", "extremist"),
        ("Расовая ненависть должна процветать", "extremist"),
        ("Свержение власти неизбежно", "extremist")
    ]
    
    print("=== ФИНАЛЬНЫЙ ТЕСТ КЛАССИФИКАТОРА ===\n")
    print("Проверяем исправление проблемы с высоким риск-скором для обычных текстов\n")
    
    correct_classifications = 0
    total_tests = len(test_texts)
    
    for i, (text, expected) in enumerate(test_texts, 1):
        print(f"Тест {i}: {text}")
        print(f"Ожидаемая классификация: {expected}")
        print("-" * 60)
        
        # Используем rule-based анализ напрямую
        rule_result = classifier.analyze_text_rule_based(text)
        risk_score = rule_result.get('risk_score', 0)
        
        # Определяем классификацию на основе риск-скора
        if risk_score >= 2:
            actual_classification = "extremist"
        else:
            actual_classification = "normal"
        
        print(f"Фактическая классификация: {actual_classification}")
        print(f"Риск-скор: {risk_score:.2f}")
        
        if rule_result.get('found_keywords'):
            print(f"Найденные ключевые слова: {rule_result['found_keywords']}")
        
        if rule_result.get('risk_factors'):
            print(f"Факторы риска: {rule_result['risk_factors']}")
        
        # Проверяем правильность классификации
        if actual_classification == expected:
            print("✅ ПРАВИЛЬНО")
            correct_classifications += 1
        else:
            print("❌ НЕПРАВИЛЬНО")
        
        print("\n" + "="*70 + "\n")
    
    # Итоговая статистика
    accuracy = (correct_classifications / total_tests) * 100
    print(f"ИТОГОВАЯ СТАТИСТИКА:")
    print(f"Правильных классификаций: {correct_classifications}/{total_tests}")
    print(f"Точность: {accuracy:.1f}%")
    
    if accuracy >= 90:
        print("🎉 ОТЛИЧНО! Классификатор работает корректно!")
    elif accuracy >= 70:
        print("⚠️ ХОРОШО, но есть место для улучшений")
    else:
        print("❌ ТРЕБУЮТСЯ ДОПОЛНИТЕЛЬНЫЕ ИСПРАВЛЕНИЯ")

if __name__ == "__main__":
    final_test()