#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ai.content_classifier import ExtremistContentClassifier
import re

def check_keywords():
    classifier = ExtremistContentClassifier()
    
    # Тестовые тексты
    test_texts = [
        "Террористическая угроза должна быть устранена",
        "Призываю к насилию против всех врагов",
        "Взрывчатые вещества можно изготовить дома"
    ]
    
    print("=== ПРОВЕРКА КЛЮЧЕВЫХ СЛОВ ===\n")
    
    # Показываем словарь ключевых слов
    print("Словарь ключевых слов:")
    for category, keywords in classifier.extremist_keywords.items():
        print(f"{category}: {keywords}")
    print("\n" + "="*60 + "\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Тест {i}: {text}")
        print("-" * 50)
        text_lower = text.lower()
        
        # Проверяем каждую категорию
        for category, keywords in classifier.extremist_keywords.items():
            found_in_category = []
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text_lower):
                    found_in_category.append(keyword)
            
            if found_in_category:
                print(f"Категория {category}: {found_in_category}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    check_keywords()