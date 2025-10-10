#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль расчета индексов социальной напряженности и всплеска

Этот модуль содержит функции для:
- Расчет индекса социальной напряженности на основе контента
- Расчет индекса всплеска (срочности/экстренности)
- Анализ эмоциональной окраски текста
- Интеграция с AI-классификатором
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TensionFactors:
    """Факторы для расчета индексов напряженности"""
    category_weight: float
    keyword_matches: int
    emotional_intensity: float
    urgency_words: int
    caps_ratio: float
    exclamation_ratio: float
    ai_score: Optional[float] = None

class TensionCalculator:
    """Калькулятор индексов социальной напряженности и всплеска"""
    
    def __init__(self):
        # Веса категорий для социальной напряженности (0-1)
        self.category_weights = {
            'military_operations': 0.9,      # Военные операции - высокая напряженность
            'humanitarian_crisis': 0.8,       # Гуманитарный кризис - высокая
            'economic_consequences': 0.6,     # Экономические последствия - средняя
            'political_decisions': 0.5,       # Политические решения - средняя
            'information_social': 0.4         # Информационно-социальные - низкая
        }
        
        # Ключевые слова для социальной напряженности
        self.tension_keywords = {
            'high': [  # Высокая напряженность
                'смерть', 'убийство', 'убит', 'погиб', 'погибший', 'жертва', 'жертвы',
                'разрушение', 'разрушен', 'разрушено', 'уничтожен', 'уничтожение',
                'атака', 'атаковать', 'обстрел', 'обстрелян', 'бомбардировка',
                'кризис', 'катастрофа', 'трагедия', 'ужас', 'кошмар',
                'паника', 'паниковать', 'страх', 'бояться', 'тревога',
                'война', 'военные действия', 'конфликт', 'столкновение'
            ],
            'medium': [  # Средняя напряженность
                'проблема', 'проблемы', 'сложный', 'сложная', 'сложно',
                'опасность', 'опасный', 'опасно', 'угроза', 'угрожать',
                'беспокойство', 'беспокоиться', 'волноваться', 'волнение',
                'напряжение', 'напряженный', 'напряженно', 'стресс',
                'конфликт', 'спор', 'разногласие', 'противоречие'
            ],
            'low': [  # Низкая напряженность
                'мирный', 'мирно', 'спокойный', 'спокойно', 'стабильный',
                'успех', 'успешный', 'победа', 'победить', 'достижение',
                'прогресс', 'развитие', 'улучшение', 'улучшать',
                'сотрудничество', 'помощь', 'поддержка', 'поддерживать'
            ]
        }
        
        # Слова для индекса всплеска (срочности)
        self.urgency_keywords = {
            'critical': [  # Критическая срочность
                'срочно', 'экстренно', 'немедленно', 'сейчас же', 'прямо сейчас',
                'только что', 'только что произошло', 'в данный момент',
                'внезапно', 'неожиданно', 'мгновенно', 'молниеносно',
                'критический', 'критическая ситуация', 'чрезвычайная ситуация',
                'авария', 'катастрофа', 'взрыв', 'пожар', 'наводнение'
            ],
            'high': [  # Высокая срочность
                'быстро', 'скоро', 'в ближайшее время', 'в течение дня',
                'сегодня', 'завтра', 'на этой неделе', 'в ближайшие дни',
                'важно', 'важная новость', 'значительное событие',
                'прорыв', 'прорывное', 'революционный', 'исторический'
            ],
            'medium': [  # Средняя срочность
                'вскоре', 'в ближайшем будущем', 'планируется', 'ожидается',
                'предполагается', 'возможно', 'вероятно', 'скорее всего',
                'объявлено', 'сообщено', 'заявлено', 'отмечено'
            ]
        }
        
        # Эмоциональные маркеры
        self.emotional_markers = {
            'anger': ['гнев', 'ярость', 'злость', 'возмущение', 'негодование'],
            'fear': ['страх', 'боязнь', 'тревога', 'паника', 'ужас'],
            'sadness': ['грусть', 'печаль', 'скорбь', 'тоска', 'депрессия'],
            'joy': ['радость', 'счастье', 'восторг', 'ликование', 'празднование'],
            'surprise': ['удивление', 'изумление', 'шок', 'потрясение', 'неожиданность']
        }
    
    def calculate_social_tension(
        self,
        category: str,
        title: str,
        content: str,
        ai_score: Optional[float] = None
    ) -> float:
        """
        Рассчитывает индекс социальной напряженности (0-100)
        
        Args:
            category: Категория новости
            title: Заголовок новости
            content: Содержимое новости
            ai_score: Оценка от AI (если есть)
            
        Returns:
            float: Индекс социальной напряженности (0-100)
        """
        try:
            full_text = f"{title} {content}".lower()
            
            # Базовый вес категории
            category_weight = self.category_weights.get(category, 0.5)
            
            # Подсчет совпадений ключевых слов
            keyword_score = self._calculate_keyword_score(full_text, self.tension_keywords)
            
            # Анализ эмоциональной интенсивности
            emotional_intensity = self._calculate_emotional_intensity(full_text)
            
            # Анализ заглавных букв и восклицательных знаков
            caps_ratio = self._calculate_caps_ratio(full_text)
            exclamation_ratio = self._calculate_exclamation_ratio(full_text)
            
            # Комбинированный расчет
            base_score = category_weight * 50  # Базовый счет от категории (0-50)
            keyword_score_weighted = keyword_score * 30  # Вес ключевых слов (0-30)
            emotional_score = emotional_intensity * 15   # Эмоциональная составляющая (0-15)
            formatting_score = (caps_ratio + exclamation_ratio) * 5  # Форматирование (0-5)
            
            # Если есть AI оценка, используем ее как основной фактор
            if ai_score is not None:
                ai_weight = 0.7  # 70% веса для AI
                manual_weight = 0.3  # 30% веса для ручного расчета
                
                manual_score = base_score + keyword_score_weighted + emotional_score + formatting_score
                final_score = (ai_score * ai_weight) + (manual_score * manual_weight)
            else:
                final_score = base_score + keyword_score_weighted + emotional_score + formatting_score
            
            # Ограничиваем результат диапазоном 0-100
            result = max(0, min(100, final_score))
            
            logger.debug(f"Социальная напряженность: категория={category_weight:.2f}, "
                        f"ключевые слова={keyword_score:.2f}, эмоции={emotional_intensity:.2f}, "
                        f"форматирование={caps_ratio + exclamation_ratio:.2f}, итого={result:.2f}")
            
            return round(result, 1)
            
        except Exception as e:
            logger.error(f"Ошибка при расчете социальной напряженности: {e}")
            return 50.0  # Среднее значение при ошибке
    
    def calculate_spike_index(
        self,
        title: str,
        content: str,
        ai_score: Optional[float] = None
    ) -> float:
        """
        Рассчитывает индекс всплеска (срочности/экстренности) (0-100)
        
        Args:
            title: Заголовок новости
            content: Содержимое новости
            ai_score: Оценка от AI (если есть)
            
        Returns:
            float: Индекс всплеска (0-100)
        """
        try:
            full_text = f"{title} {content}".lower()
            
            # Подсчет срочных слов
            urgency_score = self._calculate_urgency_score(full_text)
            
            # Анализ заглавных букв в заголовке
            title_caps_ratio = self._calculate_caps_ratio(title)
            
            # Анализ восклицательных знаков
            exclamation_ratio = self._calculate_exclamation_ratio(full_text)
            
            # Анализ временных маркеров
            time_markers_score = self._calculate_time_markers_score(full_text)
            
            # Комбинированный расчет
            base_score = urgency_score * 40  # Вес срочных слов (0-40)
            caps_score = title_caps_ratio * 20  # Вес заглавных букв (0-20)
            exclamation_score = exclamation_ratio * 20  # Вес восклицательных знаков (0-20)
            time_score = time_markers_score * 20  # Вес временных маркеров (0-20)
            
            # Если есть AI оценка, используем ее как основной фактор
            if ai_score is not None:
                ai_weight = 0.7  # 70% веса для AI
                manual_weight = 0.3  # 30% веса для ручного расчета
                
                manual_score = base_score + caps_score + exclamation_score + time_score
                final_score = (ai_score * ai_weight) + (manual_score * manual_weight)
            else:
                final_score = base_score + caps_score + exclamation_score + time_score
            
            # Ограничиваем результат диапазоном 0-100
            result = max(0, min(100, final_score))
            
            logger.debug(f"Индекс всплеска: срочность={urgency_score:.2f}, "
                        f"заглавные={title_caps_ratio:.2f}, восклицания={exclamation_ratio:.2f}, "
                        f"время={time_markers_score:.2f}, итого={result:.2f}")
            
            return round(result, 1)
            
        except Exception as e:
            logger.error(f"Ошибка при расчете индекса всплеска: {e}")
            return 50.0  # Среднее значение при ошибке
    
    def _calculate_keyword_score(self, text: str, keyword_groups: Dict[str, List[str]]) -> float:
        """
        Рассчитывает оценку на основе ключевых слов
        
        Args:
            text: Текст для анализа
            keyword_groups: Группы ключевых слов с весами
            
        Returns:
            float: Оценка (0-1)
        """
        total_score = 0.0
        total_weight = 0.0
        
        for group, keywords in keyword_groups.items():
            weight = {'high': 1.0, 'medium': 0.6, 'low': 0.2}.get(group, 0.5)
            
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                # Нормализуем количество совпадений
                normalized_matches = min(matches / 5, 1.0)  # Максимум 5 совпадений = 1.0
                total_score += normalized_matches * weight
                total_weight += weight
        
        return total_score / max(total_weight, 1.0)
    
    def _calculate_urgency_score(self, text: str) -> float:
        """
        Рассчитывает оценку срочности на основе ключевых слов
        
        Args:
            text: Текст для анализа
            
        Returns:
            float: Оценка срочности (0-1)
        """
        total_score = 0.0
        total_weight = 0.0
        
        for group, keywords in self.urgency_keywords.items():
            weight = {'critical': 1.0, 'high': 0.7, 'medium': 0.4}.get(group, 0.5)
            
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                normalized_matches = min(matches / 3, 1.0)  # Максимум 3 совпадения = 1.0
                total_score += normalized_matches * weight
                total_weight += weight
        
        return total_score / max(total_weight, 1.0)
    
    def _calculate_emotional_intensity(self, text: str) -> float:
        """
        Рассчитывает эмоциональную интенсивность текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            float: Эмоциональная интенсивность (0-1)
        """
        total_intensity = 0.0
        emotion_count = 0
        
        for emotion, keywords in self.emotional_markers.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                # Разные эмоции имеют разный вес для напряженности
                emotion_weights = {
                    'anger': 0.9,
                    'fear': 0.8,
                    'sadness': 0.6,
                    'surprise': 0.5,
                    'joy': 0.2  # Радость снижает напряженность
                }
                
                weight = emotion_weights.get(emotion, 0.5)
                intensity = min(matches / 3, 1.0)  # Нормализуем
                total_intensity += intensity * weight
                emotion_count += 1
        
        return total_intensity / max(emotion_count, 1.0)
    
    def _calculate_caps_ratio(self, text: str) -> float:
        """
        Рассчитывает долю заглавных букв в тексте
        
        Args:
            text: Текст для анализа
            
        Returns:
            float: Доля заглавных букв (0-1)
        """
        if not text:
            return 0.0
        
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return 0.0
        
        caps_count = sum(1 for c in letters if c.isupper())
        return caps_count / len(letters)
    
    def _calculate_exclamation_ratio(self, text: str) -> float:
        """
        Рассчитывает долю восклицательных знаков в тексте
        
        Args:
            text: Текст для анализа
            
        Returns:
            float: Доля восклицательных знаков (0-1)
        """
        if not text:
            return 0.0
        
        total_chars = len(text)
        exclamation_count = text.count('!')
        
        # Нормализуем: максимум 5% восклицательных знаков = 1.0
        return min(exclamation_count / (total_chars * 0.05), 1.0)
    
    def _calculate_time_markers_score(self, text: str) -> float:
        """
        Рассчитывает оценку временных маркеров
        
        Args:
            text: Текст для анализа
            
        Returns:
            float: Оценка временных маркеров (0-1)
        """
        time_patterns = [
            r'\b(сегодня|завтра|вчера)\b',
            r'\b(сейчас|сейчас же|прямо сейчас)\b',
            r'\b(только что|недавно|недавно произошло)\b',
            r'\b(в данный момент|в настоящее время)\b',
            r'\b(в ближайшее время|скоро|вскоре)\b',
            r'\b(в течение дня|на этой неделе)\b'
        ]
        
        matches = 0
        for pattern in time_patterns:
            matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Нормализуем: максимум 3 совпадения = 1.0
        return min(matches / 3, 1.0)
    
    def get_tension_factors(
        self,
        category: str,
        title: str,
        content: str,
        ai_social_tension: Optional[float] = None,
        ai_spike_index: Optional[float] = None
    ) -> TensionFactors:
        """
        Возвращает все факторы для анализа напряженности
        
        Args:
            category: Категория новости
            title: Заголовок новости
            content: Содержимое новости
            ai_social_tension: AI оценка социальной напряженности
            ai_spike_index: AI оценка индекса всплеска
            
        Returns:
            TensionFactors: Все факторы напряженности
        """
        full_text = f"{title} {content}".lower()
        
        return TensionFactors(
            category_weight=self.category_weights.get(category, 0.5),
            keyword_matches=sum(1 for keywords in self.tension_keywords.values() 
                               for keyword in keywords if keyword in full_text),
            emotional_intensity=self._calculate_emotional_intensity(full_text),
            urgency_words=sum(1 for keywords in self.urgency_keywords.values() 
                             for keyword in keywords if keyword in full_text),
            caps_ratio=self._calculate_caps_ratio(full_text),
            exclamation_ratio=self._calculate_exclamation_ratio(full_text),
            ai_score=ai_social_tension
        )


# Глобальный экземпляр калькулятора
tension_calculator = TensionCalculator()


def calculate_social_tension(
    category: str,
    title: str,
    content: str,
    ai_score: Optional[float] = None
) -> float:
    """
    Удобная функция для расчета социальной напряженности
    
    Args:
        category: Категория новости
        title: Заголовок новости
        content: Содержимое новости
        ai_score: Оценка от AI
        
    Returns:
        float: Индекс социальной напряженности (0-100)
    """
    return tension_calculator.calculate_social_tension(category, title, content, ai_score)


def calculate_spike_index(
    title: str,
    content: str,
    ai_score: Optional[float] = None
) -> float:
    """
    Удобная функция для расчета индекса всплеска
    
    Args:
        title: Заголовок новости
        content: Содержимое новости
        ai_score: Оценка от AI
        
    Returns:
        float: Индекс всплеска (0-100)
    """
    return tension_calculator.calculate_spike_index(title, content, ai_score)


def calculate_both_indices(
    category: str,
    title: str,
    content: str,
    ai_social_tension: Optional[float] = None,
    ai_spike_index: Optional[float] = None
) -> Tuple[float, float]:
    """
    Удобная функция для расчета обоих индексов
    
    Args:
        category: Категория новости
        title: Заголовок новости
        content: Содержимое новости
        ai_social_tension: AI оценка социальной напряженности
        ai_spike_index: AI оценка индекса всплеска
        
    Returns:
        Tuple[float, float]: (социальная напряженность, индекс всплеска)
    """
    social_tension = tension_calculator.calculate_social_tension(
        category, title, content, ai_social_tension
    )
    spike_index = tension_calculator.calculate_spike_index(
        title, content, ai_spike_index
    )
    
    return social_tension, spike_index


if __name__ == "__main__":
    # Тестирование калькулятора
    test_cases = [
        ("military_operations", "СРОЧНО! Российские войска нанесли удар по складу боеприпасов!", 
         "В результате атаки уничтожен склад с боеприпасами в Харьковской области. Пострадавших среди мирного населения нет."),
        ("humanitarian_crisis", "Более 10 тысяч беженцев пересекли границу", 
         "За последние сутки через пограничные пункты в Польшу прошло более 10 тысяч украинских беженцев."),
        ("economic_consequences", "Курс рубля упал на 8%", 
         "После введения новых санкций курс рубля к доллару упал на 8% на Московской бирже."),
        ("political_decisions", "Президент объявил о введении военного положения", 
         "Президент Украины подписал указ о введении военного положения в приграничных регионах."),
        ("information_social", "В соцсетях распространилась фейковая запись", 
         "В социальных сетях активно распространяется фейковая запись о взрыве в центре Киева.")
    ]
    
    print("Тестирование TensionCalculator:")
    print("=" * 60)
    
    for i, (category, title, content) in enumerate(test_cases, 1):
        print(f"\nТест {i}:")
        print(f"Категория: {category}")
        print(f"Заголовок: {title}")
        print(f"Контент: {content}")
        
        social_tension = calculate_social_tension(category, title, content)
        spike_index = calculate_spike_index(title, content)
        
        print(f"Результаты:")
        print(f"  Социальная напряженность: {social_tension}")
        print(f"  Индекс всплеска: {spike_index}")
        
        # Получаем факторы для детального анализа
        factors = tension_calculator.get_tension_factors(category, title, content)
        print(f"  Факторы:")
        print(f"    Вес категории: {factors.category_weight}")
        print(f"    Совпадения ключевых слов: {factors.keyword_matches}")
        print(f"    Эмоциональная интенсивность: {factors.emotional_intensity:.2f}")
        print(f"    Срочные слова: {factors.urgency_words}")
        print(f"    Доля заглавных букв: {factors.caps_ratio:.2f}")
        print(f"    Доля восклицательных знаков: {factors.exclamation_ratio:.2f}")
