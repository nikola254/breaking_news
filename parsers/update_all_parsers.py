#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматического обновления всех парсеров новостей
для работы с украинскими категориями и фильтрацией релевантности.
"""

import os
import shutil
from datetime import datetime

def backup_parser(parser_path):
    """Создает резервную копию парсера"""
    backup_path = f"{parser_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(parser_path, backup_path)
    print(f"✓ Создана резервная копия: {backup_path}")
    return backup_path

def update_parser_file(parser_path):
    """Обновляет один файл парсера"""
    
    # Извлекаем имя источника из имени файла
    filename = os.path.basename(parser_path)
    source_name = filename.replace('parser_', '').replace('.py', '')
    
    print(f"\n=== Обновление парсера {source_name} ===")
    
    # Создаем резервную копию
    backup_parser(parser_path)
    
    # Читаем содержимое файла
    try:
        with open(parser_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"✗ Ошибка при чтении файла {parser_path}: {e}")
        return False
    
    # Применяем обновления
    try:
        print("• Обновление импортов...")
        # Добавляем импорт фильтра украинской релевантности
        if 'from ukraine_relevance_filter import filter_ukraine_relevance' not in content:
            content = content.replace(
                'from news_categories import',
                'from news_categories import'
            )
            content = content.replace(
                'from news_categories import classify_news, classify_news_ai',
                'from news_categories import classify_news, classify_news_ai\nfrom ukraine_relevance_filter import filter_ukraine_relevance'
            )
        
        print("• Обновление функции создания таблиц...")
        # Заменяем вызов функции создания таблиц
        content = content.replace(
            'create_table_if_not_exists()',
            'create_ukraine_tables_if_not_exists()'
        )
        
        # Добавляем новую функцию создания украинских таблиц
        if 'def create_ukraine_tables_if_not_exists():' not in content:
            # Находим место после импортов и добавляем новую функцию
            import_end = content.find('def create_table_if_not_exists():')
            if import_end != -1:
                new_function = f'''
def create_ukraine_tables_if_not_exists():
    """Создает таблицы для украинских категорий"""
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Создаем таблицы для украинских категорий
    ukraine_categories = [
        'military_operations',      # Военные операции
        'humanitarian_crisis',      # Гуманитарный кризис
        'economic_consequences',    # Экономические последствия
        'political_decisions',      # Политические решения
        'information_social',       # Информационно-социальные аспекты
        'other'                     # Прочее
    ]
    
    for category in ukraine_categories:
        table_name = f"news.{source_name}_{category}"
        
        if '{source_name}' == 'telegram':
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                content String,
                channel String,
                message_id Int64,
                message_link String,
                source String DEFAULT 'telegram',
                category String DEFAULT '{category}',
                relevance_score Float32 DEFAULT 0.0,
                ai_confidence Float32 DEFAULT 0.0,
                keywords_found Array(String) DEFAULT [],
                sentiment_score Float32 DEFAULT 0.0,
                tension_score Float32 DEFAULT 0.0,
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (published_date, id)
            """
        elif '{source_name}' == 'israil':
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                source_links String,
                source String DEFAULT '7kanal.co.il',
                category String DEFAULT '{category}',
                relevance_score Float32 DEFAULT 0.0,
                ai_confidence Float32 DEFAULT 0.0,
                keywords_found Array(String) DEFAULT [],
                sentiment_score Float32 DEFAULT 0.0,
                tension_score Float32 DEFAULT 0.0,
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (published_date, id)
            """
        else:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                source String DEFAULT '{source_name}',
                category String DEFAULT '{category}',
                relevance_score Float32 DEFAULT 0.0,
                ai_confidence Float32 DEFAULT 0.0,
                keywords_found Array(String) DEFAULT [],
                sentiment_score Float32 DEFAULT 0.0,
                tension_score Float32 DEFAULT 0.0,
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (published_date, id)
            """
        
        client.execute(sql)
        print(f"Создана таблица {table_name}")

'''
                content = content[:import_end] + new_function + content[import_end:]
        
        print("• Добавление фильтрации украинской релевантности...")
        # Добавляем проверку релевантности перед классификацией
        if 'filter_ukraine_relevance(title, content)' not in content:
            content = content.replace(
                'category = classify_news_ai(title, content)',
                '''# Проверяем релевантность к украинскому конфликту
            print("Проверка релевантности к украинскому конфликту...")
            relevance_result = filter_ukraine_relevance(title, content)
            
            if not relevance_result['is_relevant']:
                print(f"Статья не релевантна украинскому конфликту (score: {relevance_result['relevance_score']:.2f})")
                print("Пропускаем статью...")
                continue
            
            print(f"Статья релевантна (score: {relevance_result['relevance_score']:.2f})")
            print(f"Найденные ключевые слова: {relevance_result['keywords_found']}")
            
            # Классифицируем новость по украинским категориям
            try:
                category = classify_news_ai(title, content)
            except Exception as e:
                print(f"AI классификация не удалась: {e}")
                category = 'other'  # Fallback категория'''
            )
        
        print("• Обновление структуры данных...")
        # Обновляем структуру данных для включения украинских полей
        content = content.replace(
            "'title': title,\n                'link': link,\n                'content': content",
            "'title': title,\n                'link': link,\n                'content': content,\n                'source': source_name,\n                'category': category,\n                'relevance_score': relevance_result['relevance_score'],\n                'ai_confidence': relevance_result.get('ai_confidence', 0.0),\n                'keywords_found': relevance_result['keywords_found'],\n                'sentiment_score': 0.0,\n                'published_date': datetime.now(),\n                'published_date': datetime.now()"
        )
        
        # Записываем обновленное содержимое
        with open(parser_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Парсер {source_name} успешно обновлен")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при обновлении парсера {source_name}: {e}")
        return False

def main():
    """Основная функция для обновления всех парсеров"""
    
    print("=== Автоматическое обновление всех парсеров для украинских категорий ===")
    
    # Получаем путь к директории парсеров
    parsers_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Список парсеров для обновления
    parsers_to_update = [
        'parser_lenta.py', 
        'parser_rbc.py',
        'parser_rt.py',
        'parser_gazeta.py',
        'parser_kommersant.py',
        'parser_cnn.py',
        'parser_bbc.py',
        'parser_reuters.py',
        'parser_aljazeera.py',
        'parser_euronews.py',
        'parser_france24.py',
        'parser_dw.py',
        'parser_tsn.py',
        'parser_unian.py',
        'parser_israil.py',
        'parser_telegram.py'
    ]
    
    updated_count = 0
    failed_count = 0
    
    for parser_file in parsers_to_update:
        parser_path = os.path.join(parsers_dir, parser_file)
        
        if os.path.exists(parser_path):
            if update_parser_file(parser_path):
                updated_count += 1
            else:
                failed_count += 1
        else:
            print(f"⚠ Файл {parser_file} не найден, пропускаем")
    
    print(f"\n=== Результаты обновления ===")
    print(f"✓ Успешно обновлено: {updated_count} парсеров")
    print(f"✗ Ошибки при обновлении: {failed_count} парсеров")
    print(f"⚠ Пропущено: {len(parsers_to_update) - updated_count - failed_count} парсеров")
    
    if updated_count > 0:
        print("\n🎉 Все парсеры успешно адаптированы для работы с украинскими категориями!")
        print("\nТеперь парсеры будут:")
        print("• Фильтровать только релевантные украинскому конфликту новости")
        print("• Классифицировать по 5 новым украинским категориям")
        print("• Сохранять данные в новые таблицы с расширенными полями")
        print("• Записывать метрики релевантности и уверенности AI")
    
    print("\nДля применения изменений запустите:")
    print("python init_ukraine_database.py")

if __name__ == '__main__':
    main()
