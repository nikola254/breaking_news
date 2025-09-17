#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ конкретного поста на экстремистский контент
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.ai.content_classifier import ExtremistContentClassifier

def analyze_post():
    # Анализируемый текст
    text = 'Служба внешней разведки России выпустила сборник рассекреченных документов времён Великой Отечественной войны. #Россия @new_militarycolumnist'
    
    print('🔍 Анализ поста о СВР России')
    print('=' * 80)
    print(f'Текст: {text}')
    print()
    
    classifier = ExtremistContentClassifier()
    
    # Старая система
    print('СТАРАЯ СИСТЕМА:')
    old_result = classifier.analyze_extremism_percentage(text)
    print(f'  • Процент экстремизма: {old_result.get("extremism_percentage", 0)}%')
    print(f'  • Уровень риска: {old_result.get("risk_level", "none")}')
    print(f'  • Метод: {old_result.get("method", "unknown")}')
    print()
    
    # Новая система ФЗ-114
    print('НОВАЯ СИСТЕМА ФЗ-114:')
    new_result = classifier.analyze_extremism_fz114(text)
    print(f'  • Процент экстремизма: {new_result["extremism_percentage"]}%')
    print(f'  • Уровень риска: {new_result["risk_level"]}')
    print(f'  • Экстремистский: {new_result["is_extremist"]}')
    
    if new_result['fz114_violations']:
        print(f'  • Нарушения ФЗ-114: {", ".join(new_result["fz114_violations"])}')
    
    if new_result['detected_categories']:
        print(f'  • Обнаруженные категории:')
        for category, details in new_result['detected_categories'].items():
            print(f'    - {category}: {details["keywords"]} (серьезность: {details["severity"]})')
    
    if new_result['threat_patterns_found']:
        print(f'  • Паттерны угроз: {len(new_result["threat_patterns_found"])}')
    
    if new_result['hate_speech_patterns_found']:
        print(f'  • Паттерны языка вражды: {len(new_result["hate_speech_patterns_found"])}')
    
    print(f'  • Объяснение: {new_result["explanation"]}')
    print()
    
    print('📊 АНАЛИЗ РЕЗУЛЬТАТОВ:')
    print('-' * 40)
    
    old_percentage = old_result.get('extremism_percentage', 0)
    new_percentage = new_result['extremism_percentage']
    
    if new_percentage == 0:
        print('✅ Пост НЕ содержит экстремистского контента согласно ФЗ-114')
    else:
        print('⚠️ Обнаружены признаки экстремистского контента')
    
    if old_percentage > 50:
        print('❌ Старая система дала ложноположительный результат')
        print('💡 Рекомендация: использовать новую систему ФЗ-114 для более точной оценки')
    
    print(f'\n🔄 Сравнение систем:')
    print(f'  Старая система: {old_percentage}% экстремизма')
    print(f'  Новая система ФЗ-114: {new_percentage}% экстремизма')
    print(f'  Разница: {abs(old_percentage - new_percentage)}%')
    
    # Объяснение почему старая система могла дать высокий процент
    print(f'\n🤔 ВОЗМОЖНЫЕ ПРИЧИНЫ ВЫСОКОЙ ОЦЕНКИ СТАРОЙ СИСТЕМЫ:')
    print('1. Облачная модель может реагировать на слова "разведка", "Россия"')
    print('2. Контекст военной тематики (Великая Отечественная война)')
    print('3. Упоминание государственных структур')
    print('4. Недостаточная настройка модели на различение новостного и экстремистского контента')
    
    print(f'\n✅ ПРЕИМУЩЕСТВА НОВОЙ СИСТЕМЫ ФЗ-114:')
    print('1. Точное соответствие российскому законодательству')
    print('2. Анализ конкретных признаков экстремизма, а не общих слов')
    print('3. Различение новостного контента от экстремистского')
    print('4. Детальное объяснение с указанием статей закона')

if __name__ == "__main__":
    analyze_post()