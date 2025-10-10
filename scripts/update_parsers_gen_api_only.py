#!/usr/bin/env python3
"""
Скрипт для обновления всех парсеров для использования только Gen-API классификатора
"""

import os
import re
import glob

def update_parser_for_gen_api(file_path):
    """Обновляет парсер для использования только Gen-API классификатора"""
    print(f"🔄 Обновляем парсер: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Удаляем импорт старой классификации
        replacements = [
            # Удаляем импорт старой классификации
            (r'from parsers\.news_categories import classify_news, create_category_tables\n', ''),
            (r'from parsers\.news_categories import classify_news\n', ''),
            (r'from parsers\.news_categories import create_category_tables\n', ''),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # Добавляем логику Gen-API классификации после фильтра релевантности
        # Ищем место, где используется filter_ukraine_relevance
        relevance_pattern = r'(relevance_result = filter_ukraine_relevance\([^)]+\)\s*\n)'
        
        if re.search(relevance_pattern, content):
            # Заменяем логику классификации
            new_classification_logic = '''relevance_result = filter_ukraine_relevance(title, content)
            
            # Дополнительная классификация через Gen-API для получения индексов напряженности
            try:
                from parsers.gen_api_classifier import GenApiNewsClassifier
                classifier = GenApiNewsClassifier()
                ai_result = classifier.classify(title, content)
                
                # Объединяем результаты
                category = relevance_result.get('category', ai_result['category_name'])
                social_tension_index = ai_result['social_tension_index']
                spike_index = ai_result['spike_index']
                ai_confidence = ai_result['confidence']
                ai_category = ai_result['category_name']
                
            except Exception as e:
                logger.warning(f"Ошибка Gen-API классификации: {e}")
                # Fallback к результатам фильтра релевантности
                category = relevance_result.get('category', 'other')
                social_tension_index = 0.0
                spike_index = 0.0
                ai_confidence = 0.0
                ai_category = category
'''
            
            content = re.sub(relevance_pattern, new_classification_logic, content)
            
            # Обновляем логику сохранения для включения новых полей
            save_pattern = r"(client\.execute\(\s*'INSERT INTO news\.\w+_headlines \([^)]+\) VALUES',\s*\[\([^)]+\)\]\s*\))"
            
            def update_save_logic(match):
                old_save = match.group(1)
                # Извлекаем поля из старого INSERT
                fields_match = re.search(r'INSERT INTO news\.(\w+)_headlines \(([^)]+)\) VALUES', old_save)
                if fields_match:
                    table_name = fields_match.group(1)
                    old_fields = fields_match.group(2)
                    
                    # Добавляем новые поля
                    new_fields = old_fields + ', social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata'
                    
                    # Обновляем VALUES
                    values_match = re.search(r'\[\(([^)]+)\)\]', old_save)
                    if values_match:
                        old_values = values_match.group(1)
                        new_values = old_values + f', {social_tension_index}, {spike_index}, "{ai_category}", {ai_confidence}, "gen_api_classification"'
                        
                        new_save = old_save.replace(old_fields, new_fields).replace(old_values, new_values)
                        return new_save
                
                return old_save
            
            content = re.sub(save_pattern, update_save_logic, content)
        
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
    """Обновляет все парсеры для использования только Gen-API"""
    print("🔄 ОБНОВЛЕНИЕ ВСЕХ ПАРСЕРОВ ДЛЯ GEN-API")
    print("=" * 60)
    
    # Находим все файлы парсеров
    parser_files = glob.glob("parsers/parser_*.py")
    
    updated_count = 0
    total_count = len(parser_files)
    
    for file_path in parser_files:
        if update_parser_for_gen_api(file_path):
            updated_count += 1
    
    print(f"\n📊 Итоговая статистика:")
    print(f"   Всего файлов: {total_count}")
    print(f"   Обновлено: {updated_count}")
    print(f"   Без изменений: {total_count - updated_count}")

if __name__ == "__main__":
    update_all_parsers()
