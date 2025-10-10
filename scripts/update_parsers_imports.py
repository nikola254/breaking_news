#!/usr/bin/env python3
"""
Скрипт для обновления всех парсеров
Заменяет старые импорты на новые Gen-API классификаторы
"""

import os
import re
import glob

def update_parser_file(file_path):
    """Обновляет один файл парсера"""
    print(f"🔄 Обновляем: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Заменяем импорты
        replacements = [
            # Старые импорты AI классификатора
            (r'from ai_news_classifier import classify_news_ai', 'from parsers.gen_api_classifier import GenApiNewsClassifier'),
            (r'import ai_news_classifier', 'from parsers.gen_api_classifier import GenApiNewsClassifier'),
            
            # Заменяем вызовы классификации
            (r'classify_news_ai\(([^)]+)\)', r'GenApiNewsClassifier().classify(\1)'),
            
            # Обновляем логику сохранения для включения новых полей
            (r'(\s+)(\w+)\s*=\s*classify_news\([^)]+\)', r'\1classification_result = GenApiNewsClassifier().classify(title, content)\n\1category = classification_result["category_name"]\n\1confidence = classification_result["confidence"]\n\1social_tension_index = classification_result["social_tension_index"]\n\1spike_index = classification_result["spike_index"]'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # Если файл изменился, сохраняем
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Обновлен: {file_path}")
            return True
        else:
            print(f"ℹ️ Без изменений: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обновлении {file_path}: {e}")
        return False

def update_all_parsers():
    """Обновляет все парсеры"""
    print("🔄 ОБНОВЛЕНИЕ ВСЕХ ПАРСЕРОВ")
    print("=" * 50)
    
    # Находим все файлы парсеров
    parser_files = glob.glob("parsers/parser_*.py")
    
    updated_count = 0
    total_count = len(parser_files)
    
    for file_path in parser_files:
        if update_parser_file(file_path):
            updated_count += 1
    
    print(f"\n📊 Итоговая статистика:")
    print(f"   Всего файлов: {total_count}")
    print(f"   Обновлено: {updated_count}")
    print(f"   Без изменений: {total_count - updated_count}")

if __name__ == "__main__":
    update_all_parsers()
