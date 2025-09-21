# -*- coding: utf-8 -*-
"""
Модуль для анализа социальной напряженности на основе новостей.

Этот модуль содержит алгоритмы для:
- Расчета индекса социальной напряженности
- Анализа эмоциональной окраски новостей
- Определения трендов напряженности
- Классификации уровней напряженности
"""

import re
import math
import requests
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from textblob import TextBlob
import logging
from config import Config

@dataclass
class TensionMetrics:
    """Метрики социальной напряженности."""
    tension_score: float  # Общий индекс напряженности (0-100)
    emotional_intensity: float  # Эмоциональная интенсивность (0-100)
    conflict_level: float  # Уровень конфликтности (0-100)
    urgency_factor: float  # Фактор срочности (0-100)
    category: str  # Категория напряженности
    trend: str  # Тренд (rising, falling, stable)

class SocialTensionAnalyzer:
    """Анализатор социальной напряженности."""
    
    # Ключевые слова для определения напряженности
    TENSION_KEYWORDS = {
        'high_tension': [
            'война', 'конфликт', 'атака', 'обстрел', 'взрыв', 'убийство', 'смерть',
            'разрушение', 'жертвы', 'раненые', 'погибшие', 'теракт', 'бомбардировка',
            'ракетный удар', 'авиаудар', 'артобстрел', 'снайпер', 'диверсия',
            'эвакуация', 'беженцы', 'паника', 'хаос', 'катастрофа', 'трагедия'
        ],
        'medium_tension': [
            'напряжение', 'угроза', 'опасность', 'тревога', 'беспокойство',
            'протест', 'демонстрация', 'митинг', 'забастовка', 'блокада',
            'санкции', 'ультиматум', 'предупреждение', 'мобилизация',
            'учения', 'маневры', 'переговоры', 'кризис', 'инцидент'
        ],
        'low_tension': [
            'мир', 'стабильность', 'спокойствие', 'безопасность', 'порядок',
            'восстановление', 'помощь', 'поддержка', 'сотрудничество',
            'договор', 'соглашение', 'перемирие', 'гуманитарная помощь'
        ]
    }
    
    # Эмоциональные маркеры
    EMOTIONAL_MARKERS = {
        'negative': [
            'ужас', 'страх', 'боль', 'горе', 'отчаяние', 'ярость', 'гнев',
            'ненависть', 'злость', 'возмущение', 'шок', 'ужасно', 'страшно',
            'кошмар', 'катастрофа', 'трагедия', 'беда', 'несчастье'
        ],
        'positive': [
            'надежда', 'радость', 'счастье', 'облегчение', 'спокойствие',
            'уверенность', 'оптимизм', 'победа', 'успех', 'достижение',
            'прогресс', 'улучшение', 'восстановление', 'мир', 'безопасность'
        ]
    }
    
    # Маркеры срочности
    URGENCY_MARKERS = [
        'срочно', 'экстренно', 'немедленно', 'сейчас', 'прямо сейчас',
        'в данный момент', 'только что', 'сегодня', 'вчера', 'сегодня утром',
        'breaking', 'urgent', 'alert', 'внимание', 'важно'
    ]
    
    def __init__(self):
        """Инициализация анализатора."""
        self.tension_weights = {
            'high_tension': 3.0,
            'medium_tension': 2.0,
            'low_tension': -1.0
        }
        self.emotional_weights = {
            'negative': 2.0,
            'positive': -1.0
        }
        self.api_cloud_enabled = (
            hasattr(Config, 'API_CLOUD_URL') and 
            hasattr(Config, 'API_CLOUD_KEY') and
            Config.API_CLOUD_URL is not None and 
            Config.API_CLOUD_KEY is not None and
            Config.API_CLOUD_URL.strip() != '' and
            Config.API_CLOUD_KEY.strip() != ''
        )
        self.logger = logging.getLogger(__name__)
        
        # Логируем статус API_CLOUD
        if self.api_cloud_enabled:
            self.logger.info("API_CLOUD интеграция включена")
        else:
            self.logger.info("API_CLOUD интеграция отключена - работаем в автономном режиме")
    
    def analyze_text_tension(self, text: str, title: str = "") -> TensionMetrics:
        """
        Анализ напряженности текста новости.
        
        Args:
            text: Текст новости
            title: Заголовок новости
            
        Returns:
            TensionMetrics: Метрики напряженности
        """
        if not text:
            return TensionMetrics(0, 0, 0, 0, "low", "stable")
        
        # Объединяем заголовок и текст для анализа
        full_text = f"{title} {text}".lower()
        
        # Расчет базовых метрик
        tension_score = self._calculate_tension_score(full_text)
        emotional_intensity = self._calculate_emotional_intensity(full_text)
        conflict_level = self._calculate_conflict_level(full_text)
        urgency_factor = self._calculate_urgency_factor(full_text)
        
        # Общий индекс напряженности
        overall_tension = self._calculate_overall_tension(
            tension_score, emotional_intensity, conflict_level, urgency_factor
        )
        
        # Определение категории
        category = self._determine_category(overall_tension)
        
        # Если доступен API_CLOUD, используем его для улучшения анализа
        if self.api_cloud_enabled:
            try:
                cloud_sentiment = self._analyze_with_api_cloud(full_text)
                if cloud_sentiment:
                    # Корректируем оценки на основе данных API_CLOUD
                    overall_tension = self._adjust_tension_with_cloud(overall_tension, cloud_sentiment)
                    emotional_intensity = self._adjust_emotion_with_cloud(emotional_intensity, cloud_sentiment)
            except Exception as e:
                self.logger.warning(f"API_CLOUD analysis failed: {e}")

        return TensionMetrics(
            tension_score=overall_tension,
            emotional_intensity=emotional_intensity,
            conflict_level=conflict_level,
            urgency_factor=urgency_factor,
            category=category,
            trend="stable"  # Тренд определяется при анализе временных рядов
        )
    
    def _calculate_tension_score(self, text: str) -> float:
        """Расчет базового индекса напряженности."""
        score = 0.0
        word_count = len(text.split())
        
        if word_count == 0:
            return 0.0
        
        for category, keywords in self.TENSION_KEYWORDS.items():
            weight = self.tension_weights[category]
            for keyword in keywords:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
                score += count * weight
        
        # Нормализация по количеству слов
        normalized_score = (score / word_count) * 100
        return min(max(normalized_score, 0), 100)
    
    def _calculate_emotional_intensity(self, text: str) -> float:
        """Расчет эмоциональной интенсивности."""
        score = 0.0
        word_count = len(text.split())
        
        if word_count == 0:
            return 0.0
        
        for category, markers in self.EMOTIONAL_MARKERS.items():
            weight = self.emotional_weights[category]
            for marker in markers:
                count = len(re.findall(r'\b' + re.escape(marker) + r'\b', text))
                score += count * weight
        
        # Учитываем восклицательные знаки и заглавные буквы
        exclamation_count = text.count('!')
        caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        
        score += exclamation_count * 0.5 + caps_ratio * 10
        
        normalized_score = (score / word_count) * 100
        return min(max(normalized_score, 0), 100)
    
    def _calculate_conflict_level(self, text: str) -> float:
        """Расчет уровня конфликтности."""
        conflict_keywords = [
            'против', 'враг', 'противник', 'борьба', 'сражение', 'битва',
            'столкновение', 'противостояние', 'конфронтация', 'агрессия',
            'нападение', 'захват', 'оккупация', 'вторжение', 'наступление'
        ]
        
        score = 0.0
        word_count = len(text.split())
        
        if word_count == 0:
            return 0.0
        
        for keyword in conflict_keywords:
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
            score += count * 2.0
        
        normalized_score = (score / word_count) * 100
        return min(max(normalized_score, 0), 100)
    
    def _calculate_urgency_factor(self, text: str) -> float:
        """Расчет фактора срочности."""
        score = 0.0
        word_count = len(text.split())
        
        if word_count == 0:
            return 0.0
        
        for marker in self.URGENCY_MARKERS:
            count = len(re.findall(r'\b' + re.escape(marker) + r'\b', text))
            score += count * 1.5
        
        # Учитываем временные маркеры
        time_markers = ['сегодня', 'вчера', 'сейчас', 'только что', 'минуту назад']
        for marker in time_markers:
            if marker in text:
                score += 2.0
        
        normalized_score = (score / word_count) * 100
        return min(max(normalized_score, 0), 100)
    
    def _calculate_overall_tension(self, tension: float, emotional: float, 
                                 conflict: float, urgency: float) -> float:
        """Расчет общего индекса напряженности."""
        # Проверяем входные данные на корректность
        def safe_value(value):
            if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
                return 0.0
            return float(value)
        
        tension = safe_value(tension)
        emotional = safe_value(emotional)
        conflict = safe_value(conflict)
        urgency = safe_value(urgency)
        
        # Взвешенная сумма всех компонентов
        weights = {
            'tension': 0.4,
            'emotional': 0.25,
            'conflict': 0.25,
            'urgency': 0.1
        }
        
        overall = (
            tension * weights['tension'] +
            emotional * weights['emotional'] +
            conflict * weights['conflict'] +
            urgency * weights['urgency']
        )
        
        # Проверяем результат на корректность
        if math.isnan(overall) or math.isinf(overall):
            return 0.0
        
        return min(max(overall, 0), 100)
    
    def _determine_category(self, tension_score: float) -> str:
        """Определение категории напряженности."""
        if tension_score >= 70:
            return "critical"
        elif tension_score >= 50:
            return "high"
        elif tension_score >= 30:
            return "medium"
        elif tension_score >= 10:
            return "low"
        else:
            return "minimal"
    
    def analyze_trend(self, tension_history: List[Tuple[datetime, float]], 
                     window_size: int = 24) -> str:
        """
        Анализ тренда напряженности.
        
        Args:
            tension_history: История значений напряженности [(datetime, tension_score)]
            window_size: Размер окна для анализа тренда (в часах)
            
        Returns:
            str: Тренд ('rising', 'falling', 'stable')
        """
        if len(tension_history) < 2:
            return "stable"
        
        # Сортируем по времени
        sorted_history = sorted(tension_history, key=lambda x: x[0])
        
        # Берем последние значения в пределах окна
        now = datetime.now()
        cutoff_time = now - timedelta(hours=window_size)
        recent_values = [
            score for timestamp, score in sorted_history 
            if timestamp >= cutoff_time
        ]
        
        if len(recent_values) < 2:
            return "stable"
        
        # Вычисляем тренд с помощью линейной регрессии
        x = np.arange(len(recent_values))
        y = np.array(recent_values)
        
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            
            if slope > 2.0:
                return "rising"
            elif slope < -2.0:
                return "falling"
            else:
                return "stable"
        
        return "stable"
    
    def get_tension_distribution(self, tensions: List[float]) -> Dict[str, int]:
        """
        Получение распределения напряженности по категориям.
        
        Args:
            tensions: Список значений напряженности
            
        Returns:
            Dict: Распределение по категориям
        """
        distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "minimal": 0
        }
        
        for tension in tensions:
            category = self._determine_category(tension)
            distribution[category] += 1
        
        return distribution
    
    def _analyze_with_api_cloud(self, text: str) -> Dict:
        """Анализ текста через API_CLOUD."""
        try:
            if not self.api_cloud_enabled:
                return None
            
            # Дополнительная проверка на корректность URL
            if not Config.API_CLOUD_URL or Config.API_CLOUD_URL == 'None':
                self.logger.warning("API_CLOUD_URL не настроен или равен 'None'")
                return None
            
            # Подготавливаем запрос к API_CLOUD
            headers = {
                'Authorization': f'Bearer {Config.API_CLOUD_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'text': text[:2000],  # Ограничиваем длину текста
                'language': 'ru',
                'analysis_type': 'sentiment_emotion',
                'include_emotions': True,
                'include_intensity': True
            }
            
            response = requests.post(
                f"{Config.API_CLOUD_URL}/analyze/sentiment",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"API_CLOUD returned status {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error calling API_CLOUD: {e}")
            return None
    
    def _adjust_tension_with_cloud(self, base_tension: float, cloud_data: Dict) -> float:
        """Корректировка напряженности на основе данных API_CLOUD."""
        try:
            # Проверяем входные данные на корректность
            if not isinstance(base_tension, (int, float)) or math.isnan(base_tension) or math.isinf(base_tension):
                return 0.0
                
            if not cloud_data or 'sentiment' not in cloud_data:
                return base_tension
            
            cloud_sentiment = cloud_data['sentiment']
            cloud_confidence = cloud_data.get('confidence', 0.5)
            
            # Проверяем корректность данных от API_CLOUD
            if not isinstance(cloud_confidence, (int, float)) or math.isnan(cloud_confidence) or math.isinf(cloud_confidence):
                return base_tension
            
            # Если API_CLOUD показывает высокую негативность, увеличиваем напряженность
            negative_score = cloud_sentiment.get('negative', 0)
            if (isinstance(negative_score, (int, float)) and not math.isnan(negative_score) and 
                negative_score > 0.7 and cloud_confidence > 0.8):
                # Корректируем для диапазона 0-100
                adjustment = negative_score * 30.0  # 0.3 * 100
                result = min(100.0, base_tension + adjustment)
                return result if not math.isnan(result) and not math.isinf(result) else base_tension
            
            # Если API_CLOUD показывает позитивность, снижаем напряженность
            positive_score = cloud_sentiment.get('positive', 0)
            if (isinstance(positive_score, (int, float)) and not math.isnan(positive_score) and 
                positive_score > 0.6 and cloud_confidence > 0.8):
                # Корректируем для диапазона 0-100
                adjustment = positive_score * 20.0  # 0.2 * 100
                result = max(0.0, base_tension - adjustment)
                return result if not math.isnan(result) and not math.isinf(result) else base_tension
            
            return base_tension
            
        except Exception as e:
            self.logger.error(f"Error adjusting tension with cloud data: {e}")
            return base_tension if isinstance(base_tension, (int, float)) and not math.isnan(base_tension) else 0.0
    
    def _adjust_emotion_with_cloud(self, base_emotion: float, cloud_data: Dict) -> float:
        """Корректировка эмоциональной интенсивности на основе данных API_CLOUD."""
        try:
            # Проверяем входные данные на корректность
            if not isinstance(base_emotion, (int, float)) or math.isnan(base_emotion) or math.isinf(base_emotion):
                return 0.0
                
            if not cloud_data or 'sentiment' not in cloud_data:
                return base_emotion
            
            cloud_sentiment = cloud_data['sentiment']
            cloud_confidence = cloud_data.get('confidence', 0.5)
            
            # Проверяем корректность данных от API_CLOUD
            if not isinstance(cloud_confidence, (int, float)) or math.isnan(cloud_confidence) or math.isinf(cloud_confidence):
                return base_emotion
            
            # Усиливаем эмоциональную интенсивность при высокой уверенности API_CLOUD
            if cloud_confidence > 0.8:
                # Корректируем для диапазона 0-100
                emotion_boost = cloud_confidence * 20.0  # 0.2 * 100
                result = min(100.0, base_emotion + emotion_boost)
                return result if not math.isnan(result) and not math.isinf(result) else base_emotion
            
            return base_emotion
            
        except Exception as e:
            self.logger.error(f"Error adjusting emotion with cloud data: {e}")
            return base_emotion if isinstance(base_emotion, (int, float)) and not math.isnan(base_emotion) else 0.0

# Глобальный экземпляр анализатора
_tension_analyzer = None

def get_tension_analyzer() -> SocialTensionAnalyzer:
    """Получение глобального экземпляра анализатора напряженности."""
    global _tension_analyzer
    if _tension_analyzer is None:
        _tension_analyzer = SocialTensionAnalyzer()
    return _tension_analyzer