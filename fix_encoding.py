# -*- coding: utf-8 -*-
"""
Скрипт для исправления кодировки русского текста в файлах проекта
"""

import os
import re

def fix_encoding_in_file(file_path):
    """Исправляет кодировку в указанном файле"""
    try:
        # Читаем файл
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Исправляем кракозябры для основных категорий
        content = re.sub(r"'military_operations': '[^']*'", "'military_operations': 'Военные операции'", content)
        content = re.sub(r"'humanitarian_crisis': '[^']*'", "'humanitarian_crisis': 'Гуманитарный кризис'", content)
        content = re.sub(r"'economic_consequences': '[^']*'", "'economic_consequences': 'Экономические последствия'", content)
        content = re.sub(r"'political_decisions': '[^']*'", "'political_decisions': 'Политические решения'", content)
        content = re.sub(r"'information_social': '[^']*'", "'information_social': 'Информационно-социальные аспекты'", content)
        content = re.sub(r"'all': '[^']*'", "'all': 'Все категории'", content)
        
        # Исправляем в массивах объектов
        content = re.sub(r"'name': '[^']*', 'type': 'base'\}", "'name': 'Все категории', 'type': 'base'}", content)
        content = re.sub(r"{'id': 'all', 'name': '[^']*'", "{'id': 'all', 'name': 'Все категории'", content)
        content = re.sub(r"{'id': 'military_operations', 'name': '[^']*'", "{'id': 'military_operations', 'name': 'Военные операции'", content)
        content = re.sub(r"{'id': 'humanitarian_crisis', 'name': '[^']*'", "{'id': 'humanitarian_crisis', 'name': 'Гуманитарный кризис'", content)
        content = re.sub(r"{'id': 'economic_consequences', 'name': '[^']*'", "{'id': 'economic_consequences', 'name': 'Экономические последствия'", content)
        content = re.sub(r"{'id': 'political_decisions', 'name': '[^']*'", "{'id': 'political_decisions', 'name': 'Политические решения'", content)
        content = re.sub(r"{'id': 'information_social', 'name': '[^']*'", "{'id': 'information_social', 'name': 'Информационно-социальные аспекты'", content)
        
        # Записываем обратно, если были изменения
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Файл {file_path} обновлен")
        else:
            print(f"В файле {file_path} замены не требуются")
            
    except Exception as e:
        print(f"Ошибка при обработке файла {file_path}: {e}")

def main():
    # Список файлов для обработки
    files_to_fix = [
        'app/blueprints/forecast_api.py',
        'app/blueprints/news_api.py'
    ]
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    for file_path in files_to_fix:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"Обрабатываем файл: {full_path}")
            fix_encoding_in_file(full_path)
        else:
            print(f"Файл не найден: {full_path}")

if __name__ == "__main__":
    main()
    print("Исправление кодировки завершено!")