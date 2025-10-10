#!/usr/bin/env python3
"""
Тест обновленного парсера Lenta с Gen-API классификатором
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_lenta_parser():
    """Тестируем обновленный парсер Lenta"""
    print("🧪 ТЕСТ ПАРСЕРА LENTA С GEN-API")
    print("=" * 50)
    
    try:
        from parsers.parser_lenta import parse_lenta_news
        
        print("✅ Парсер Lenta успешно импортирован")
        
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
    success = test_lenta_parser()
    
    if success:
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n❌ Тест не прошел")
