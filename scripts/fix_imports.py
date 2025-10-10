#!/usr/bin/env python3
"""
Скрипт для исправления импортов во всех парсерах
"""

import os
import re
import glob

def fix_imports_in_file(file_path):
    """Исправляет импорты в одном файле"""
    print(f"🔧 Исправляем импорты: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Исправления импортов
        replacements = [
            # Исправляем импорты модулей из parsers
            (r'from news_categories import', 'from parsers.news_categories import'),
            (r'from ukraine_relevance_filter import', 'from parsers.ukraine_relevance_filter import'),
            (r'from duplicate_checker import', 'from parsers.duplicate_checker import'),
            (r'from content_validator import', 'from parsers.content_validator import'),
            (r'from news_preprocessor import', 'from parsers.news_preprocessor import'),
            (r'from tension_calculator import', 'from parsers.tension_calculator import'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # Если файл изменился, сохраняем
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Исправлен: {file_path}")
            return True
        else:
            print(f"ℹ️ Без изменений: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при исправлении {file_path}: {e}")
        return False

def fix_all_imports():
    """Исправляет импорты во всех парсерах"""
    print("🔧 ИСПРАВЛЕНИЕ ИМПОРТОВ ВО ВСЕХ ПАРСЕРАХ")
    print("=" * 50)
    
    # Находим все файлы парсеров
    parser_files = glob.glob("parsers/parser_*.py")
    
    fixed_count = 0
    total_count = len(parser_files)
    
    for file_path in parser_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print(f"\n📊 Итоговая статистика:")
    print(f"   Всего файлов: {total_count}")
    print(f"   Исправлено: {fixed_count}")
    print(f"   Без изменений: {total_count - fixed_count}")

if __name__ == "__main__":
    fix_all_imports()
