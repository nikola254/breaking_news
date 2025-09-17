#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматического обновления всех парсеров с новым AI-фильтром релевантности
"""

import os
import re
import glob

def update_parser_file(file_path):
    """Обновляет один файл парсера с новым фильтром релевантности"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, нужно ли обновлять файл
        if 'ukraine_relevance_filter' in content:
            print(f"Файл {file_path} уже обновлен")
            return False
            
        # Добавляем импорт фильтра релевантности
        import_pattern = r'(from news_categories import classify_news, create_category_tables)'
        import_replacement = r'\1\nfrom ukraine_relevance_filter import filter_ukraine_relevance'
        
        if re.search(import_pattern, content):
            content = re.sub(import_pattern, import_replacement, content)
        else:
            print(f"Не найден паттерн импорта в {file_path}")
            return False
        
        # Заменяем логику классификации
        old_classification_pattern = r'''            # Классификация новости
            try:

                # Проверяем релевантность к украинскому конфликту
            print\("Проверка релевантности к украинскому конфликту\.\.\."\)
            relevance_result = filter_ukraine_relevance\(title, content\)
            
            if not relevance_result\['is_relevant'\]:
                print\(f"Статья не релевантна украинскому конфликту \(score: \{relevance_result\['relevance_score'\]:.2f\}\)"\)
                print\("Пропускаем статью\.\.\."\)
                continue
            
            print\(f"Статья релевантна \(score: \{relevance_result\['relevance_score'\]:.2f\}\)"\)
            print\(f"Найденные ключевые слова: \{relevance_result\['keywords_found'\]\}"\)
            
            # Классифицируем новость по украинским категориям
            try:
                category = classify_news_ai\(title, content\)
            except Exception as e:
                print\(f"AI классификация не удалась: \{e\}"\)
                category = 'other'  # Fallback категория

            except Exception as e:

                print\(f"AI классификация не удалась: \{e\}"\)

                category = classify_news\(title, content\)'''
        
        new_classification = '''            # Проверяем релевантность к украинскому конфликту
            logger.info("Проверка релевантности к украинскому конфликту...")
            relevance_result = filter_ukraine_relevance(title, content)
            
            if not relevance_result['is_relevant']:
                logger.info(f"Статья не релевантна украинскому конфликту (score: {relevance_result['relevance_score']:.2f})")
                continue
            
            logger.info(f"Статья релевантна (score: {relevance_result['relevance_score']:.2f}, категория: {relevance_result['category']})")
            logger.info(f"Найденные ключевые слова: {relevance_result['keywords_found']}")
            
            # Используем категорию из фильтра релевантности
            category = relevance_result['category']'''
        
        # Ищем и заменяем старую логику классификации
        if re.search(old_classification_pattern, content, re.MULTILINE | re.DOTALL):
            content = re.sub(old_classification_pattern, new_classification, content, flags=re.MULTILINE | re.DOTALL)
        else:
            # Ищем альтернативные паттерны классификации
            alt_pattern1 = r'(# Классификация новости[\s\S]*?category = classify_news\(title, content\))'
            alt_pattern2 = r'(try:[\s\S]*?category = classify_news_ai\(title, content\)[\s\S]*?except[\s\S]*?category = classify_news\(title, content\))'
            
            if re.search(alt_pattern1, content):
                content = re.sub(alt_pattern1, new_classification, content)
            elif re.search(alt_pattern2, content):
                content = re.sub(alt_pattern2, new_classification, content)
            else:
                print(f"Не найден паттерн классификации в {file_path}")
                return False
        
        # Сохраняем обновленный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Успешно обновлен файл: {file_path}")
        return True
        
    except Exception as e:
        print(f"Ошибка при обновлении файла {file_path}: {e}")
        return False

def main():
    """Главная функция для обновления всех парсеров"""
    parsers_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Находим все файлы парсеров
    parser_files = glob.glob(os.path.join(parsers_dir, 'parser_*.py'))
    
    # Исключаем уже обновленные файлы и служебные файлы
    exclude_files = [
        'parser_lenta.py',  # уже обновлен
        'parser_tsn.py',    # уже обновлен
        'parser_unian.py',  # уже обновлен
        'parser_example_with_ai.py',
        'parser_manager.py',
        'parser_telegram.py'  # требует особой обработки
    ]
    
    parser_files = [f for f in parser_files if os.path.basename(f) not in exclude_files]
    
    print(f"Найдено {len(parser_files)} файлов парсеров для обновления")
    
    updated_count = 0
    for parser_file in parser_files:
        print(f"\nОбновление {os.path.basename(parser_file)}...")
        if update_parser_file(parser_file):
            updated_count += 1
    
    print(f"\nОбновление завершено. Обновлено файлов: {updated_count}/{len(parser_files)}")

if __name__ == "__main__":
    main()