#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работоспособности всех парсеров
"""

import sys
import os
import traceback
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_classifier():
    """Тестирует классификатор новостей"""
    print("🔍 Тестирование классификатора...")
    
    try:
        from parsers.improved_classifier import ImprovedNewsClassifier
        
        classifier = ImprovedNewsClassifier()
        
        # Тестовые новости
        test_news = [
            {
                'title': 'ВС РФ нанесли мощный удар по военным объектам Украины',
                'content': 'Российские военные провели успешную операцию по уничтожению военной инфраструктуры противника',
                'expected': 'military_operations'
            },
            {
                'title': 'Эвакуация мирных жителей из зоны боевых действий',
                'content': 'Гуманитарные коридоры работают для спасения гражданского населения',
                'expected': 'humanitarian_crisis'
            },
            {
                'title': 'Санкции против России ударили по экономике',
                'content': 'Западные санкции привели к росту цен и инфляции',
                'expected': 'economic_consequences'
            },
            {
                'title': 'Путин встретился с лидерами стран СНГ',
                'content': 'Президент России обсудил вопросы сотрудничества с коллегами',
                'expected': 'political_decisions'
            },
            {
                'title': 'Новый фильм о войне в Украине',
                'content': 'Кинематографисты снимают документальный фильм о событиях',
                'expected': 'information_social'
            }
        ]
        
        correct = 0
        total = len(test_news)
        
        for i, news in enumerate(test_news, 1):
            category, confidence, scores = classifier.classify(news['title'], news['content'])
            expected = news['expected']
            
            print(f"  Тест {i}: {news['title'][:50]}...")
            print(f"    Ожидалось: {expected}")
            print(f"    Получено: {category} (уверенность: {confidence:.2f})")
            
            if category == expected:
                correct += 1
                print("    ✅ ПРАВИЛЬНО")
            else:
                print("    ❌ ОШИБКА")
            print()
        
        accuracy = (correct / total) * 100
        print(f"📊 Точность классификатора: {accuracy:.1f}% ({correct}/{total})")
        
        return accuracy > 60  # Минимальная приемлемая точность
        
    except Exception as e:
        print(f"❌ Ошибка тестирования классификатора: {e}")
        traceback.print_exc()
        return False

def test_parser_imports():
    """Тестирует импорт всех парсеров"""
    print("📦 Тестирование импорта парсеров...")
    
    parsers = [
        'parser_ria', 'parser_lenta', 'parser_rbc', 'parser_gazeta',
        'parser_kommersant', 'parser_cnn', 'parser_bbc', 'parser_dw',
        'parser_euronews', 'parser_france24', 'parser_reuters', 'parser_rt',
        'parser_telegram', 'parser_twitter', 'parser_unian', 'parser_tsn',
        'parser_aljazeera', 'parser_israil'
    ]
    
    working_parsers = []
    broken_parsers = []
    
    for parser_name in parsers:
        try:
            module = __import__(f'parsers.{parser_name}', fromlist=[parser_name])
            working_parsers.append(parser_name)
            print(f"  ✅ {parser_name}")
        except Exception as e:
            broken_parsers.append((parser_name, str(e)))
            print(f"  ❌ {parser_name}: {e}")
    
    print(f"\n📊 Результат импорта:")
    print(f"  Работающих парсеров: {len(working_parsers)}")
    print(f"  Сломанных парсеров: {len(broken_parsers)}")
    
    if broken_parsers:
        print("\n🔧 Сломанные парсеры:")
        for parser, error in broken_parsers:
            print(f"  - {parser}: {error}")
    
    return len(broken_parsers) == 0

def test_database_connection():
    """Тестирует подключение к базе данных"""
    print("🗄️ Тестирование подключения к ClickHouse...")
    
    try:
        from clickhouse_driver import Client
        from config import Config
        
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Тестовый запрос
        result = client.execute('SELECT 1')
        print("  ✅ Подключение к ClickHouse успешно")
        
        # Проверяем существование базы данных
        databases = client.execute('SHOW DATABASES')
        db_names = [row[0] for row in databases]
        
        if 'news' in db_names:
            print("  ✅ База данных 'news' существует")
        else:
            print("  ⚠️ База данных 'news' не найдена")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка подключения к ClickHouse: {e}")
        return False

def test_table_creation():
    """Тестирует создание таблиц без дублирования полей"""
    print("🏗️ Тестирование создания таблиц...")
    
    try:
        from clickhouse_driver import Client
        from config import Config
        
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Создаем тестовую таблицу
        test_table_sql = """
        CREATE TABLE IF NOT EXISTS news.test_table (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            content String,
            published_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (published_date, id)
        """
        
        client.execute(test_table_sql)
        print("  ✅ Создание тестовой таблицы успешно")
        
        # Удаляем тестовую таблицу
        client.execute('DROP TABLE IF EXISTS news.test_table')
        print("  ✅ Удаление тестовой таблицы успешно")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка создания таблицы: {e}")
        return False

def test_news_preprocessing():
    """Тестирует предобработку новостей"""
    print("🔧 Тестирование предобработки новостей...")
    
    try:
        from parsers.news_preprocessor import NewsPreprocessor
        
        preprocessor = NewsPreprocessor()
        
        # Тестовый текст
        test_text = """
        ❗️⚡🔥 ВАЖНО! Подписывайся на наш канал!
        
        ВС РФ нанесли мощный удар по военным объектам.
        
        https://example.com/news/123
        
        Читайте нас для получения актуальных новостей!
        """
        
        cleaned = preprocessor.clean_text(test_text)
        
        print(f"  Исходный текст: {test_text[:100]}...")
        print(f"  Очищенный текст: {cleaned[:100]}...")
        
        # Проверяем, что реклама удалена
        if 'подписывайся' not in cleaned.lower() and 'https://' not in cleaned:
            print("  ✅ Предобработка работает корректно")
            return True
        else:
            print("  ❌ Предобработка работает некорректно")
            return False
            
    except Exception as e:
        print(f"  ❌ Ошибка тестирования предобработки: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск комплексного тестирования парсеров")
    print("=" * 60)
    
    tests = [
        ("Классификатор новостей", test_classifier),
        ("Импорт парсеров", test_parser_imports),
        ("Подключение к БД", test_database_connection),
        ("Создание таблиц", test_table_creation),
        ("Предобработка новостей", test_news_preprocessing),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results[test_name] = False
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("📋 ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"  {test_name}: {status}")
    
    print(f"\n📊 Общий результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️ Некоторые тесты провалены. Требуется исправление.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
