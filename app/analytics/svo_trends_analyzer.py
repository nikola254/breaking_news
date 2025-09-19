"""
Модуль для анализа трендов и статистики по темам СВО (Специальная военная операция)
Анализирует динамику интереса к темам СВО с 2022-2025 годы и социальную напряженность
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class TrendData:
    """Структура данных для трендов"""
    date: datetime
    interest_level: float
    social_tension: float
    mentions_count: int
    sentiment_score: float
    keywords: List[str]

@dataclass
class SVOAnalysisResult:
    """Результат анализа СВО трендов"""
    period_start: datetime
    period_end: datetime
    total_mentions: int
    avg_interest_level: float
    avg_social_tension: float
    trend_direction: str  # 'rising', 'falling', 'stable'
    peak_dates: List[datetime]
    low_dates: List[datetime]
    key_events: List[Dict]

class SVOTrendsAnalyzer:
    """Анализатор трендов по темам СВО"""
    
    def __init__(self):
        self.svo_keywords = [
            'СВО', 'специальная военная операция', 'спецоперация',
            'Украина', 'Донбасс', 'ЛНР', 'ДНР', 'Запорожье', 'Херсон',
            'мобилизация', 'частичная мобилизация', 'военкомат',
            'санкции', 'антироссийские санкции', 'экономические санкции',
            'НАТО', 'военная помощь', 'оружие Украине',
            'беженцы', 'эвакуация', 'гуманитарная помощь',
            'переговоры', 'мирные переговоры', 'дипломатия'
        ]
        
        self.tension_indicators = [
            'протест', 'митинг', 'недовольство', 'возмущение',
            'против войны', 'антивоенный', 'пацифист',
            'экономический кризис', 'инфляция', 'рост цен',
            'безработица', 'сокращения', 'банкротство',
            'эмиграция', 'отъезд', 'релокация', 'бегство'
        ]
    
    def generate_synthetic_data(self, start_date: datetime, end_date: datetime) -> List[TrendData]:
        """
        Генерирует синтетические данные для демонстрации трендов СВО
        Показывает падение интереса и рост социальной напряженности
        """
        data = []
        current_date = start_date
        
        # Базовые параметры для моделирования
        base_interest = 100.0  # Начальный уровень интереса (февраль 2022)
        base_tension = 20.0    # Начальный уровень напряженности
        
        days_total = (end_date - start_date).days
        
        while current_date <= end_date:
            # Расчет дней с начала СВО
            days_since_start = (current_date - start_date).days
            progress = days_since_start / days_total
            
            # Моделирование падения интереса (экспоненциальное затухание)
            interest_decay = np.exp(-progress * 2.5)  # Быстрое падение в первый год
            seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * days_since_start / 365.25)  # Сезонные колебания
            
            interest_level = base_interest * interest_decay * seasonal_factor
            
            # Добавляем всплески интереса в ключевые даты
            if self._is_key_event_date(current_date):
                interest_level *= 1.8  # Всплеск интереса
            
            # Моделирование роста социальной напряженности
            tension_growth = 1 + progress * 3  # Линейный рост с ускорением
            economic_pressure = 1 + 0.5 * progress  # Экономическое давление
            
            social_tension = base_tension * tension_growth * economic_pressure
            
            # Добавляем шум и случайные события
            noise_interest = np.random.normal(0, interest_level * 0.1)
            noise_tension = np.random.normal(0, social_tension * 0.05)
            
            interest_level = max(5, interest_level + noise_interest)  # Минимум 5%
            social_tension = max(10, min(100, social_tension + noise_tension))  # 10-100%
            
            # Количество упоминаний коррелирует с интересом
            mentions_count = int(interest_level * np.random.uniform(50, 150))
            
            # Sentiment становится более негативным со временем
            base_sentiment = 0.2 - progress * 0.6  # От +0.2 до -0.4
            sentiment_score = base_sentiment + np.random.normal(0, 0.1)
            
            data.append(TrendData(
                date=current_date,
                interest_level=round(interest_level, 2),
                social_tension=round(social_tension, 2),
                mentions_count=mentions_count,
                sentiment_score=round(sentiment_score, 3),
                keywords=self._get_trending_keywords(current_date, progress)
            ))
            
            current_date += timedelta(days=7)  # Еженедельные данные
        
        return data
    
    def _is_key_event_date(self, date: datetime) -> bool:
        """Определяет ключевые даты для всплесков интереса"""
        key_dates = [
            datetime(2022, 2, 24),  # Начало СВО
            datetime(2022, 9, 21),  # Частичная мобилизация
            datetime(2022, 10, 8),  # Взрыв на Крымском мосту
            datetime(2023, 6, 24),  # События с ЧВК Вагнер
            datetime(2024, 3, 22),  # Теракт в Крокусе
            datetime(2024, 8, 6),   # Курская операция
        ]
        
        for key_date in key_dates:
            if abs((date - key_date).days) <= 7:  # ±7 дней от ключевой даты
                return True
        return False
    
    def _get_trending_keywords(self, date: datetime, progress: float) -> List[str]:
        """Возвращает актуальные ключевые слова для периода"""
        if progress < 0.1:  # Первые месяцы
            return ['СВО', 'Украина', 'санкции', 'беженцы']
        elif progress < 0.3:  # Первый год
            return ['мобилизация', 'военкомат', 'эмиграция', 'протест']
        elif progress < 0.6:  # Второй год
            return ['экономический кризис', 'инфляция', 'против войны', 'переговоры']
        else:  # Поздний период
            return ['усталость от войны', 'социальная напряженность', 'экономические проблемы']
    
    def analyze_trends(self, data: List[TrendData]) -> SVOAnalysisResult:
        """Анализирует тренды в данных"""
        if not data:
            raise ValueError("Нет данных для анализа")
        
        # Сортируем по дате
        data.sort(key=lambda x: x.date)
        
        period_start = data[0].date
        period_end = data[-1].date
        
        # Базовая статистика
        total_mentions = sum(d.mentions_count for d in data)
        avg_interest = np.mean([d.interest_level for d in data])
        avg_tension = np.mean([d.social_tension for d in data])
        
        # Определение тренда интереса
        interest_values = [d.interest_level for d in data]
        trend_slope = np.polyfit(range(len(interest_values)), interest_values, 1)[0]
        
        if trend_slope > 1:
            trend_direction = 'rising'
        elif trend_slope < -1:
            trend_direction = 'falling'
        else:
            trend_direction = 'stable'
        
        # Поиск пиков и спадов
        peak_dates = self._find_peaks(data, 'interest_level', threshold=0.8)
        low_dates = self._find_peaks(data, 'interest_level', threshold=0.2, find_lows=True)
        
        # Ключевые события
        key_events = self._identify_key_events(data)
        
        return SVOAnalysisResult(
            period_start=period_start,
            period_end=period_end,
            total_mentions=total_mentions,
            avg_interest_level=round(avg_interest, 2),
            avg_social_tension=round(avg_tension, 2),
            trend_direction=trend_direction,
            peak_dates=peak_dates,
            low_dates=low_dates,
            key_events=key_events
        )
    
    def _find_peaks(self, data: List[TrendData], field: str, threshold: float, find_lows: bool = False) -> List[datetime]:
        """Находит пики или спады в данных"""
        values = [getattr(d, field) for d in data]
        dates = [d.date for d in data]
        
        if find_lows:
            # Ищем минимумы
            peaks = []
            for i in range(1, len(values) - 1):
                if (values[i] < values[i-1] and values[i] < values[i+1] and 
                    values[i] < np.percentile(values, threshold * 100)):
                    peaks.append(dates[i])
        else:
            # Ищем максимумы
            peaks = []
            for i in range(1, len(values) - 1):
                if (values[i] > values[i-1] and values[i] > values[i+1] and 
                    values[i] > np.percentile(values, threshold * 100)):
                    peaks.append(dates[i])
        
        return peaks
    
    def _identify_key_events(self, data: List[TrendData]) -> List[Dict]:
        """Идентифицирует ключевые события на основе данных"""
        events = []
        
        # Ищем резкие изменения в интересе
        for i in range(1, len(data)):
            prev_interest = data[i-1].interest_level
            curr_interest = data[i].interest_level
            
            if prev_interest and prev_interest != 0:
                change_percent = abs(curr_interest - prev_interest) / prev_interest * 100
                
                if change_percent > 50:  # Изменение более 50%
                    event_type = "Резкий рост интереса" if curr_interest > prev_interest else "Резкое падение интереса"
                    events.append({
                        'date': data[i].date.isoformat(),
                        'type': event_type,
                        'description': f"Изменение интереса на {change_percent:.1f}%",
                        'interest_level': curr_interest,
                        'social_tension': data[i].social_tension
                    })
        
        return events[:10]  # Возвращаем топ-10 событий
    
    def get_correlation_analysis(self, data: List[TrendData]) -> Dict:
        """Анализ корреляций между различными метриками"""
        if len(data) < 2:
            return {}
        
        df = pd.DataFrame([{
            'interest_level': d.interest_level,
            'social_tension': d.social_tension,
            'mentions_count': d.mentions_count,
            'sentiment_score': d.sentiment_score
        } for d in data])
        
        correlation_matrix = df.corr()
        
        return {
            'interest_tension_correlation': round(correlation_matrix.loc['interest_level', 'social_tension'], 3),
            'interest_sentiment_correlation': round(correlation_matrix.loc['interest_level', 'sentiment_score'], 3),
            'tension_sentiment_correlation': round(correlation_matrix.loc['social_tension', 'sentiment_score'], 3),
            'mentions_interest_correlation': round(correlation_matrix.loc['mentions_count', 'interest_level'], 3)
        }
    
    def get_period_comparison(self, data: List[TrendData]) -> Dict:
        """Сравнение различных периодов"""
        if len(data) < 4:
            return {}
        
        # Разделяем на периоды
        quarter_size = len(data) // 4
        
        periods = {
            'early_2022': data[:quarter_size],
            'late_2022': data[quarter_size:quarter_size*2],
            'early_2023': data[quarter_size*2:quarter_size*3],
            'recent': data[quarter_size*3:]
        }
        
        comparison = {}
        for period_name, period_data in periods.items():
            if period_data:
                comparison[period_name] = {
                    'avg_interest': round(np.mean([d.interest_level for d in period_data]), 2),
                    'avg_tension': round(np.mean([d.social_tension for d in period_data]), 2),
                    'avg_sentiment': round(np.mean([d.sentiment_score for d in period_data]), 3),
                    'total_mentions': sum(d.mentions_count for d in period_data)
                }
        
        return comparison