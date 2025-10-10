#!/usr/bin/env python3
"""
Тест обновленного UkraineRelevanceFilter с Gen-API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ukraine_filter():
    """Тестируем обновленный фильтр релевантности"""
    print("🧪 ТЕСТ UKRAINE RELEVANCE FILTER")
    print("=" * 50)
    
    try:
        from parsers.ukraine_relevance_filter import UkraineRelevanceFilter
        
        print("✅ UkraineRelevanceFilter успешно импортирован")
        
        # Создаем экземпляр
        filter_obj = UkraineRelevanceFilter()
        print("✅ Экземпляр фильтра создан")
        
        # Тестируем на украинской новости
        test_title = "Российские войска атакуют позиции ВСУ в Донецкой области"
        test_content = "Сегодня утром российские военные начали массированный обстрел позиций Вооруженных сил Украины в Донецкой области. По предварительным данным, есть потери среди военных."
        
        print(f"📰 Тестируем статью: {test_title}")
        
        from parsers.ukraine_relevance_filter import filter_ukraine_relevance
        result = filter_ukraine_relevance(test_title, test_content)
        
        print(f"✅ Результат фильтрации:")
        print(f"   Релевантна: {result['is_relevant']}")
        print(f"   Уверенность: {result['confidence']}")
        print(f"   Оценка: {result['relevance_score']}")
        print(f"   Категория: {result.get('category', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ukraine_filter()
    
    if success:
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n❌ Тест не прошел")
