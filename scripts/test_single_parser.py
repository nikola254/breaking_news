#!/usr/bin/env python3
"""
Простой тест одного парсера для проверки работы Gen-API классификатора
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_single_parser():
    """Тестируем один парсер"""
    print("🧪 ТЕСТ ОДНОГО ПАРСЕРА")
    print("=" * 40)
    
    try:
        # Импортируем функцию парсера Lenta
        from parsers.parser_lenta import parse_lenta_news
        
        print("✅ Функция парсера Lenta успешно импортирована")
        
        # Запускаем парсинг с ограничением
        print("🚀 Запускаем парсинг (максимум 2 статьи)...")
        articles_count = parse_lenta_news()
        
        print(f"✅ Парсинг завершен: обработано {articles_count} статей")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_parser()
    
    if success:
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n❌ Тест не прошел")
