#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматической миграции всех парсеров на AI классификацию
Заменяет вызовы classify_news на classify_news_ai с fallback
"""

import os
import re
from pathlib import Path

def backup_file(file_path):
    """Создает резервную копию файла"""
    backup_path = f"{file_path}.backup"
    with open(file_path, 'r', encoding='utf-8') as original:
        with open(backup_path, 'w', encoding='utf-8') as backup:
            backup.write(original.read())
    print(f"✅ Создана резервная копия: {backup_path}")

def update_parser_file(file_path):
    """Обновляет файл парсера для использования AI классификации"""
    print(f"\n🔄 Обрабатываем файл: {file_path}")
    
    # Читаем содержимое файла
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Проверяем, есть ли уже импорт AI классификатора
    if 'from .ai_news_classifier import classify_news_ai' in content or 'from ai_news_classifier import classify_news_ai' in content:
        print("⚠️  AI классификатор уже импортирован, пропускаем")
        return False
    
    # Ищем импорт news_categories
    news_categories_import_pattern = r'from \.?news_categories import classify_news'
    if re.search(news_categories_import_pattern, content):
        # Заменяем импорт на AI версию с fallback
        new_import = '''from .ai_news_classifier import classify_news_ai
from .news_categories import classify_news'''
        content = re.sub(news_categories_import_pattern, new_import, content)
        print("✅ Обновлен импорт классификатора")
    else:
        # Добавляем импорт в начало файла после существующих импортов
        import_lines = []
        other_lines = []
        in_imports = True
        
        for line in content.split('\n'):
            if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == '' or line.startswith('#')):
                import_lines.append(line)
            else:
                in_imports = False
                other_lines.append(line)
        
        # Добавляем новые импорты
        import_lines.extend([
            'from .ai_news_classifier import classify_news_ai',
            'from .news_categories import classify_news'
        ])
        
        content = '\n'.join(import_lines + other_lines)
        print("✅ Добавлены импорты классификаторов")
    
    # Заменяем вызовы classify_news на AI версию с fallback
    # Ищем паттерн: category = classify_news(title, content)
    classify_pattern = r'(\s*)(\w+)\s*=\s*classify_news\(([^)]+)\)'
    
    def replace_classify_call(match):
        indent = match.group(1)
        var_name = match.group(2)
        params = match.group(3)
        
        return f'''{indent}try:
{indent}    {var_name} = classify_news_ai({params})
{indent}except Exception as e:
{indent}    print(f"AI классификация не удалась: {{e}}")
{indent}    {var_name} = classify_news({params})'''
    
    new_content = re.sub(classify_pattern, replace_classify_call, content)
    
    if new_content != content:
        print("✅ Заменены вызовы classify_news на AI версию")
        content = new_content
    
    # Сохраняем изменения, если они были
    if content != original_content:
        # Создаем резервную копию
        backup_file(file_path)
        
        # Сохраняем обновленный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Файл успешно обновлен")
        return True
    else:
        print("ℹ️  Изменения не требуются")
        return False

def main():
    """Основная функция миграции"""
    print("🚀 Начинаем миграцию парсеров на AI классификацию")
    print("=" * 60)
    
    # Список файлов парсеров для обновления
    parser_files = [
        'parsers/parser_bbc.py',
        'parsers/parser_lenta.py', 
        'parsers/parser_unian.py',
        'parsers/parser_france24.py',
        'parsers/parser_ria.py',
        'parsers/parser_israil.py',
        'parsers/parser_dw.py',
        'parsers/parser_tsn.py',
        'parsers/parser_euronews.py',
        'parsers/parser_rt.py',
        'parsers/parser_rbc.py',
        'parsers/parser_reuters.py',
        'parsers/parser_cnn.py',
        'parsers/parser_kommersant.py',
        'parsers/parser_aljazeera.py',
        'parsers/parser_gazeta.py',
        'parsers/universal_parser.py'
    ]
    
    updated_files = []
    skipped_files = []
    
    for parser_file in parser_files:
        file_path = Path(parser_file)
        
        if not file_path.exists():
            print(f"⚠️  Файл не найден: {parser_file}")
            skipped_files.append(parser_file)
            continue
        
        try:
            if update_parser_file(file_path):
                updated_files.append(parser_file)
            else:
                skipped_files.append(parser_file)
        except Exception as e:
            print(f"❌ Ошибка при обработке {parser_file}: {e}")
            skipped_files.append(parser_file)
    
    # Итоговая статистика
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ МИГРАЦИИ")
    print("=" * 60)
    print(f"✅ Обновлено файлов: {len(updated_files)}")
    print(f"⚠️  Пропущено файлов: {len(skipped_files)}")
    
    if updated_files:
        print("\n🔄 Обновленные файлы:")
        for file in updated_files:
            print(f"  - {file}")
    
    if skipped_files:
        print("\n⏭️  Пропущенные файлы:")
        for file in skipped_files:
            print(f"  - {file}")
    
    print("\n💡 Рекомендации:")
    print("  1. Проверьте работу парсеров после миграции")
    print("  2. Убедитесь, что API_KEY настроен в .env")
    print("  3. Резервные копии созданы с расширением .backup")
    print("  4. При необходимости можно откатить изменения из .backup файлов")
    
    print("\n🎉 Миграция завершена!")

if __name__ == "__main__":
    main()