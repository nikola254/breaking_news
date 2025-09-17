# -*- coding: utf-8 -*-
"""
Анализатор тональности для украинских новостей.

Этот модуль содержит специализированный анализатор тональности,
оптимизированный для анализа новостей о украинском конфликте.
Поддерживает русский и украинский языки.
"""

import re
from typing import Dict, List, Tuple
from textblob import TextBlob
import logging

logger = logging.getLogger(__name__)

class UkraineSentimentAnalyzer:
    """Анализатор тональности для украинских новостей"""
    
    def __init__(self):
        """Инициализация анализатора"""
        self.positive_keywords = self._load_positive_keywords()
        self.negative_keywords = self._load_negative_keywords()
        self.neutral_keywords = self._load_neutral_keywords()
        self.military_keywords = self._load_military_keywords()
        self.humanitarian_keywords = self._load_humanitarian_keywords()
        
    def _load_positive_keywords(self) -> List[str]:
        """Загрузка позитивных ключевых слов"""
        return [
            # Русские позитивные слова
            'мир', 'перемирие', 'соглашение', 'договор', 'переговоры', 'дипломатия',
            'помощь', 'поддержка', 'восстановление', 'реконструкция', 'возвращение',
            'освобождение', 'победа', 'успех', 'прогресс', 'улучшение', 'стабилизация',
            'безопасность', 'защита', 'спасение', 'эвакуация', 'гуманитарный',
            
            # Украинские позитивные слова
            'мир', 'перемир\'я', 'угода', 'договір', 'переговори', 'дипломатія',
            'допомога', 'підтримка', 'відновлення', 'реконструкція', 'повернення',
            'визволення', 'перемога', 'успіх', 'прогрес', 'поліпшення', 'стабілізація',
            'безпека', 'захист', 'порятунок', 'евакуація', 'гуманітарний',
            
            # Английские позитивные слова
            'peace', 'ceasefire', 'agreement', 'treaty', 'negotiations', 'diplomacy',
            'help', 'support', 'restoration', 'reconstruction', 'return',
            'liberation', 'victory', 'success', 'progress', 'improvement', 'stabilization',
            'security', 'protection', 'rescue', 'evacuation', 'humanitarian'
        ]
    
    def _load_negative_keywords(self) -> List[str]:
        """Загрузка негативных ключевых слов"""
        return [
            # Русские негативные слова
            'война', 'конфликт', 'атака', 'обстрел', 'бомбардировка', 'взрыв',
            'убийство', 'смерть', 'жертвы', 'потери', 'разрушение', 'уничтожение',
            'блокада', 'осада', 'захват', 'оккупация', 'агрессия', 'вторжение',
            'кризис', 'катастрофа', 'трагедия', 'угроза', 'опасность', 'террор',
            'санкции', 'эмбарго', 'изоляция', 'давление', 'принуждение',
            
            # Украинские негативные слова
            'війна', 'конфлікт', 'атака', 'обстріл', 'бомбардування', 'вибух',
            'вбивство', 'смерть', 'жертви', 'втрати', 'руйнування', 'знищення',
            'блокада', 'облога', 'захоплення', 'окупація', 'агресія', 'вторгнення',
            'криза', 'катастрофа', 'трагедія', 'загроза', 'небезпека', 'терор',
            'санкції', 'ембарго', 'ізоляція', 'тиск', 'примус',
            
            # Английские негативные слова
            'war', 'conflict', 'attack', 'shelling', 'bombing', 'explosion',
            'killing', 'death', 'casualties', 'losses', 'destruction', 'annihilation',
            'blockade', 'siege', 'capture', 'occupation', 'aggression', 'invasion',
            'crisis', 'catastrophe', 'tragedy', 'threat', 'danger', 'terror',
            'sanctions', 'embargo', 'isolation', 'pressure', 'coercion'
        ]
    
    def _load_neutral_keywords(self) -> List[str]:
        """Загрузка нейтральных ключевых слов"""
        return [
            # Русские нейтральные слова
            'заявление', 'сообщение', 'информация', 'данные', 'статистика',
            'встреча', 'визит', 'поездка', 'командировка', 'делегация',
            'обсуждение', 'рассмотрение', 'анализ', 'изучение', 'исследование',
            'планирование', 'подготовка', 'организация', 'координация',
            
            # Украинские нейтральные слова
            'заява', 'повідомлення', 'інформація', 'дані', 'статистика',
            'зустріч', 'візит', 'поїздка', 'відрядження', 'делегація',
            'обговорення', 'розгляд', 'аналіз', 'вивчення', 'дослідження',
            'планування', 'підготовка', 'організація', 'координація',
            
            # Английские нейтральные слова
            'statement', 'message', 'information', 'data', 'statistics',
            'meeting', 'visit', 'trip', 'business trip', 'delegation',
            'discussion', 'consideration', 'analysis', 'study', 'research',
            'planning', 'preparation', 'organization', 'coordination'
        ]
    
    def _load_military_keywords(self) -> List[str]:
        """Загрузка военных ключевых слов"""
        return [
            # Русские военные термины
            'армия', 'войска', 'военные', 'солдаты', 'офицеры', 'генералы',
            'танки', 'самолеты', 'ракеты', 'артиллерия', 'авиация', 'флот',
            'операция', 'наступление', 'оборона', 'контратака', 'штурм',
            'позиции', 'фронт', 'линия', 'укрепления', 'база', 'штаб',
            
            # Украинские военные термины
            'армія', 'війська', 'військові', 'солдати', 'офіцери', 'генерали',
            'танки', 'літаки', 'ракети', 'артилерія', 'авіація', 'флот',
            'операція', 'наступ', 'оборона', 'контратака', 'штурм',
            'позиції', 'фронт', 'лінія', 'укріплення', 'база', 'штаб',
            
            # Английские военные термины
            'army', 'troops', 'military', 'soldiers', 'officers', 'generals',
            'tanks', 'aircraft', 'missiles', 'artillery', 'aviation', 'navy',
            'operation', 'offensive', 'defense', 'counterattack', 'assault',
            'positions', 'front', 'line', 'fortifications', 'base', 'headquarters'
        ]
    
    def _load_humanitarian_keywords(self) -> List[str]:
        """Загрузка гуманитарных ключевых слов"""
        return [
            # Русские гуманитарные термины
            'беженцы', 'эвакуация', 'гуманитарная помощь', 'медицинская помощь',
            'продовольствие', 'лекарства', 'одежда', 'жилье', 'убежище',
            'дети', 'женщины', 'пожилые', 'инвалиды', 'раненые', 'больные',
            'красный крест', 'ООН', 'волонтеры', 'благотворительность',
            
            # Украинские гуманитарные термины
            'біженці', 'евакуація', 'гуманітарна допомога', 'медична допомога',
            'продовольство', 'ліки', 'одяг', 'житло', 'притулок',
            'діти', 'жінки', 'похилі', 'інваліди', 'поранені', 'хворі',
            'червоний хрест', 'ООН', 'волонтери', 'благодійність',
            
            # Английские гуманитарные термины
            'refugees', 'evacuation', 'humanitarian aid', 'medical aid',
            'food', 'medicine', 'clothing', 'housing', 'shelter',
            'children', 'women', 'elderly', 'disabled', 'wounded', 'sick',
            'red cross', 'UN', 'volunteers', 'charity'
        ]
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Анализ тональности текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Словарь с результатами анализа:
            - sentiment_score: общий балл тональности (-1.0 до 1.0)
            - positive_score: позитивный балл (0.0 до 1.0)
            - negative_score: негативный балл (0.0 до 1.0)
            - neutral_score: нейтральный балл (0.0 до 1.0)
            - military_intensity: интенсивность военной тематики (0.0 до 1.0)
            - humanitarian_focus: фокус на гуманитарных вопросах (0.0 до 1.0)
        """
        try:
            if not text or not text.strip():
                return self._get_default_sentiment()
            
            # Нормализация текста
            normalized_text = self._normalize_text(text)
            
            # Подсчет ключевых слов
            positive_count = self._count_keywords(normalized_text, self.positive_keywords)
            negative_count = self._count_keywords(normalized_text, self.negative_keywords)
            neutral_count = self._count_keywords(normalized_text, self.neutral_keywords)
            military_count = self._count_keywords(normalized_text, self.military_keywords)
            humanitarian_count = self._count_keywords(normalized_text, self.humanitarian_keywords)
            
            # Анализ с помощью TextBlob (базовый)
            try:
                blob = TextBlob(text)
                textblob_polarity = blob.sentiment.polarity
            except:
                textblob_polarity = 0.0
            
            # Расчет весов
            total_keywords = positive_count + negative_count + neutral_count
            if total_keywords == 0:
                total_keywords = 1  # Избегаем деления на ноль
            
            # Нормализованные баллы
            positive_score = positive_count / total_keywords
            negative_score = negative_count / total_keywords
            neutral_score = neutral_count / total_keywords
            
            # Интенсивность военной тематики
            text_length = len(normalized_text.split())
            military_intensity = min(1.0, military_count / max(1, text_length / 10))
            humanitarian_focus = min(1.0, humanitarian_count / max(1, text_length / 10))
            
            # Общий балл тональности (комбинированный)
            keyword_sentiment = positive_score - negative_score
            combined_sentiment = (keyword_sentiment * 0.7 + textblob_polarity * 0.3)
            
            # Корректировка на основе военной тематики
            if military_intensity > 0.3:
                combined_sentiment -= 0.2  # Военная тематика снижает тональность
            
            # Корректировка на основе гуманитарной тематики
            if humanitarian_focus > 0.3:
                combined_sentiment += 0.1  # Гуманитарная тематика немного повышает
            
            # Ограничиваем диапазон
            combined_sentiment = max(-1.0, min(1.0, combined_sentiment))
            
            return {
                'sentiment_score': combined_sentiment,
                'positive_score': positive_score,
                'negative_score': negative_score,
                'neutral_score': neutral_score,
                'military_intensity': military_intensity,
                'humanitarian_focus': humanitarian_focus,
                'keyword_counts': {
                    'positive': positive_count,
                    'negative': negative_count,
                    'neutral': neutral_count,
                    'military': military_count,
                    'humanitarian': humanitarian_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return self._get_default_sentiment()
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста для анализа"""
        # Приведение к нижнему регистру
        text = text.lower()
        
        # Удаление лишних пробелов и символов
        text = re.sub(r'[^\w\s\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Подсчет ключевых слов в тексте"""
        count = 0
        for keyword in keywords:
            # Ищем точные совпадения слов
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = re.findall(pattern, text)
            count += len(matches)
        return count
    
    def _get_default_sentiment(self) -> Dict[str, float]:
        """Возвращает нейтральную тональность по умолчанию"""
        return {
            'sentiment_score': 0.0,
            'positive_score': 0.0,
            'negative_score': 0.0,
            'neutral_score': 1.0,
            'military_intensity': 0.0,
            'humanitarian_focus': 0.0,
            'keyword_counts': {
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'military': 0,
                'humanitarian': 0
            }
        }
    
    def get_sentiment_category(self, sentiment_score: float) -> str:
        """Получение категории тональности
        
        Args:
            sentiment_score: Балл тональности (-1.0 до 1.0)
            
        Returns:
            Категория: 'positive', 'negative', 'neutral'
        """
        if sentiment_score > 0.1:
            return 'positive'
        elif sentiment_score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """Анализ тональности для списка текстов
        
        Args:
            texts: Список текстов для анализа
            
        Returns:
            Список результатов анализа
        """
        results = []
        for text in texts:
            result = self.analyze_sentiment(text)
            results.append(result)
        return results
    
    def get_aggregated_sentiment(self, texts: List[str]) -> Dict[str, float]:
        """Получение агрегированной тональности для списка текстов
        
        Args:
            texts: Список текстов для анализа
            
        Returns:
            Агрегированные результаты анализа
        """
        if not texts:
            return self._get_default_sentiment()
        
        results = self.analyze_batch(texts)
        
        # Агрегация результатов
        total_sentiment = sum(r['sentiment_score'] for r in results)
        total_positive = sum(r['positive_score'] for r in results)
        total_negative = sum(r['negative_score'] for r in results)
        total_neutral = sum(r['neutral_score'] for r in results)
        total_military = sum(r['military_intensity'] for r in results)
        total_humanitarian = sum(r['humanitarian_focus'] for r in results)
        
        count = len(results)
        
        return {
            'sentiment_score': total_sentiment / count,
            'positive_score': total_positive / count,
            'negative_score': total_negative / count,
            'neutral_score': total_neutral / count,
            'military_intensity': total_military / count,
            'humanitarian_focus': total_humanitarian / count,
            'analyzed_texts_count': count
        }


# Глобальный экземпляр анализатора
_analyzer_instance = None

def get_ukraine_sentiment_analyzer() -> UkraineSentimentAnalyzer:
    """Получение глобального экземпляра анализатора тональности"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = UkraineSentimentAnalyzer()
    return _analyzer_instance


# Удобные функции для быстрого использования
def analyze_ukraine_news_sentiment(text: str) -> Dict[str, float]:
    """Быстрый анализ тональности украинской новости"""
    analyzer = get_ukraine_sentiment_analyzer()
    return analyzer.analyze_sentiment(text)

def get_ukraine_news_sentiment_category(text: str) -> str:
    """Быстрое получение категории тональности украинской новости"""
    analyzer = get_ukraine_sentiment_analyzer()
    result = analyzer.analyze_sentiment(text)
    return analyzer.get_sentiment_category(result['sentiment_score'])