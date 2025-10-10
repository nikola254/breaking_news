#!/usr/bin/env python3
"""
Скрипт для массового обновления всех парсеров для использования только Gen-API классификатора
"""

import os
import re
import glob

def update_parser_for_gen_api_only(file_path):
    """Обновляет парсер для использования только Gen-API классификатора"""
    print(f"🔄 Обновляем парсер: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. Удаляем импорт старой классификации
        content = re.sub(r'from parsers\.news_categories import classify_news, create_category_tables\n', '', content)
        content = re.sub(r'from parsers\.news_categories import classify_news\n', '', content)
        content = re.sub(r'from parsers\.news_categories import create_category_tables\n', '', content)
        
        # 2. Обновляем логику классификации
        # Ищем блок с filter_ukraine_relevance
        relevance_pattern = r'(relevance_result = filter_ukraine_relevance\([^)]+\)\s*\n\s*if not relevance_result\[\'is_relevant\'\]:[^}]+continue\s*\n\s*logger\.info\(f"Статья релевантна[^"]+\)\s*\n\s*logger\.info\(f"Найденные ключевые слова:[^"]+\)\s*\n\s*# Используем категорию из фильтра релевантности\s*\n\s*category = relevance_result\.get\(\'category\', \'other\'\))'
        
        new_classification_logic = '''relevance_result = filter_ukraine_relevance(title, content)
            
            if not relevance_result['is_relevant']:
                logger.info(f"Статья не релевантна украинскому конфликту (score: {relevance_result['relevance_score']:.2f})")
                continue
            
            logger.info(f"Статья релевантна (score: {relevance_result['relevance_score']:.2f}, категория: {relevance_result['category']})")
            logger.info(f"Найденные ключевые слова: {relevance_result['keywords_found']}")
            
            # Дополнительная классификация через Gen-API для получения индексов напряженности
            try:
                classifier = GenApiNewsClassifier()
                ai_result = classifier.classify(title, content)
                
                # Используем результаты Gen-API классификации
                category = ai_result['category_name']
                social_tension_index = ai_result['social_tension_index']
                spike_index = ai_result['spike_index']
                ai_confidence = ai_result['confidence']
                ai_category = ai_result['category_name']
                
                logger.info(f"Gen-API классификация: {category} (напряженность: {social_tension_index}, всплеск: {spike_index})")
                
            except Exception as e:
                logger.warning(f"Ошибка Gen-API классификации: {e}")
                # Fallback к результатам фильтра релевантности
                category = relevance_result.get('category', 'other')
                social_tension_index = 0.0
                spike_index = 0.0
                ai_confidence = 0.0
                ai_category = category'''
        
        content = re.sub(relevance_pattern, new_classification_logic, content, flags=re.MULTILINE | re.DOTALL)
        
        # 3. Обновляем INSERT запросы для основной таблицы
        insert_pattern = r"client\.execute\(\s*'INSERT INTO news\.(\w+)_headlines \(([^)]+)\) VALUES',\s*\[\(([^)]+)\)\]\s*\)"
        
        def update_main_insert(match):
            table_name = match.group(1)
            fields = match.group(2)
            values = match.group(3)
            
            # Добавляем новые поля
            new_fields = fields + ', social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata'
            new_values = values + ', social_tension_index, spike_index, ai_category, ai_confidence, \'gen_api_classification\''
            
            return f"client.execute(\n                'INSERT INTO news.{table_name}_headlines ({new_fields}) VALUES',\n                [({new_values})]\n            )"
        
        content = re.sub(insert_pattern, update_main_insert, content)
        
        # 4. Обновляем INSERT запросы для категорийных таблиц
        category_insert_pattern = r"client\.execute\(\s*f'INSERT INTO \{category_table\} \(([^)]+)\) VALUES',\s*\[\(([^)]+)\)\]\s*\)"
        
        def update_category_insert(match):
            fields = match.group(1)
            values = match.group(2)
            
            # Добавляем новые поля
            new_fields = fields + ', social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata'
            new_values = values + ', social_tension_index, spike_index, ai_category, ai_confidence, \'gen_api_classification\''
            
            return f"client.execute(\n                    f'INSERT INTO {{category_table}} ({new_fields}) VALUES',\n                    [({new_values})]\n                )"
        
        content = re.sub(category_insert_pattern, update_category_insert, content)
        
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
    print("🔄 ОБНОВЛЕНИЕ ВСЕХ ПАРСЕРОВ ДЛЯ GEN-API ТОЛЬКО")
    print("=" * 60)
    
    # Находим все файлы парсеров
    parser_files = glob.glob("parsers/parser_*.py")
    
    updated_count = 0
    total_count = len(parser_files)
    
    for file_path in parser_files:
        if update_parser_for_gen_api_only(file_path):
            updated_count += 1
    
    print(f"\n📊 Итоговая статистика:")
    print(f"   Всего файлов: {total_count}")
    print(f"   Обновлено: {updated_count}")
    print(f"   Без изменений: {total_count - updated_count}")

if __name__ == "__main__":
    update_all_parsers()
