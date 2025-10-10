#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-классификатор новостей на базе GigaChat API

Этот модуль содержит функции для:
- Классификации новостей по категориям с помощью GigaChat
- Расчет индексов социальной напряженности и всплеска
- Кэширование результатов для экономии токенов
- Интеграция с GigaChat API от Сбера
"""

import os
import json
import logging
import hashlib
import requests
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)

class GPTNewsClassifier:
    """AI-классификатор новостей на базе GigaChat API"""
    
    def __init__(self, key_id: Optional[str] = None, secret: Optional[str] = None, project_id: Optional[str] = None):
        """
        Инициализация классификатора
        
        Args:
            key_id: Key ID для GigaChat API
            secret: Key Secret для GigaChat API  
            project_id: Project ID для GigaChat API
        """
        self.key_id = key_id or os.environ.get('GIGACHAT_KEY_ID', 'a2512b4c794de9b61a5971a31a831ab2')
        self.secret = secret or os.environ.get('GIGACHAT_SECRET', '328eba3d08e4b929a5eeddad3110e7f7')
        self.project_id = project_id or os.environ.get('GIGACHAT_PROJECT_ID', 'dce70218-e109-47f8-9909-79e869875ac7')
        
        # Проверяем наличие учетных данных
        if not all([self.key_id, self.secret]):
            logger.warning("Не найдены учетные данные GigaChat, будет использоваться только fallback классификация")
            self.key_id = None
            self.secret = None
        
        # Настройки для GigaChat API
        self.auth_url = "https://auth.iam.sbercloud.ru/auth/system/openid/token"
        self.api_url = "https://gigachat.api.cloud.ru/api/gigachat/v1/chat/completions"
        self.access_token = None
        self.token_expires_at = None
        
        # Категории новостей
        self.categories = {
            '1': 'military_operations',
            '2': 'political_decisions', 
            '3': 'economic_impact',
            '4': 'humanitarian_crisis',
            '5': 'international_reaction',
            '6': 'cyber_operations',
            '7': 'propaganda_disinformation',
            '8': 'other'
        }
        
        # Кэш для результатов классификации
        self.cache = {}
        self.cache_file = "gpt_classifier_cache.json"
        self.load_cache()
        
        # Статистика использования
        self.stats = {
            'total_requests': 0,
            'cached_requests': 0,
            'tokens_used': 0,
            'errors': 0
        }
        
        logger.info("GPTNewsClassifier инициализирован с GigaChat API")
    
    def _get_access_token(self) -> str:
        """Получает токен доступа для GigaChat API"""
        if not self.key_id or not self.secret:
            raise Exception("Учетные данные GigaChat не настроены")
            
        try:
            # Проверяем, не истек ли токен
            if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
                return self.access_token
            
            # Получаем новый токен
            auth_data = {
                'grant_type': 'access_key',
                'client_id': self.key_id,
                'client_secret': self.secret
            }
            
            response = requests.post(self.auth_url, data=auth_data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Токен действует 1 час
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            
            logger.info("Получен новый токен доступа GigaChat")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Ошибка при получении токена GigaChat: {e}")
            raise Exception(f"Не удалось получить токен доступа: {e}")
    
    def load_cache(self):
        """Загружает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Загружен кэш: {len(self.cache)} записей")
        except Exception as e:
            logger.warning(f"Ошибка при загрузке кэша: {e}")
            self.cache = {}
    
    def save_cache(self):
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Ошибка при сохранении кэша: {e}")
    
    def _get_cache_key(self, title: str, content: str) -> str:
        """Генерирует ключ кэша для заголовка и контента"""
        text = f"{title}|{content}"
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _create_classification_prompt(self, title: str, content: str) -> str:
        """Создает промпт для классификации новости"""
        prompt = f"""Проанализируй новость и определи её категорию, индексы социальной напряженности и всплеска.

ЗАГОЛОВОК: {title}

КОНТЕНТ: {content}

КАТЕГОРИИ:
1. military_operations - Военные операции, боевые действия, атаки
2. political_decisions - Политические решения, заявления, дипломатия
3. economic_impact - Экономические последствия, санкции, торговля
4. humanitarian_crisis - Гуманитарные кризисы, беженцы, жертвы
5. international_reaction - Международная реакция, поддержка, осуждение
6. cyber_operations - Кибероперации, хакерские атаки, информационная безопасность
7. propaganda_disinformation - Пропаганда, дезинформация, фейки
8. other - Другие темы

ИНДЕКСЫ (0-100):
- social_tension_index: Насколько новость может вызвать социальную напряженность
- spike_index: Насколько новость может вызвать всплеск обсуждений

Ответь ТОЛЬКО в формате JSON:
{{
  "category_id": "номер_категории",
  "category_name": "название_категории",
  "social_tension_index": число_от_0_до_100,
  "spike_index": число_от_0_до_100,
  "confidence": число_от_0_до_1,
  "reasoning": "краткое объяснение выбора категории и индексов"
}}"""
        
        return prompt
    
    def _make_api_request(self, prompt: str) -> Dict:
        """
        Отправляет запрос к GigaChat API
        
        Args:
            prompt: Промпт для отправки
            
        Returns:
            Dict: Ответ от API
        """
        try:
            # Получаем токен доступа
            access_token = self._get_access_token()
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "model": "GigaChat",
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "max_tokens": 1000,
                    "repetition_penalty": 1.0,
                    "max_alternatives": 1
                },
                "project_id": self.project_id
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"API вернул статус {response.status_code}: {response.text}")
            
            response_data = response.json()
            
            # Подсчитываем токены
            if 'usage' in response_data:
                self.stats['tokens_used'] += response_data['usage'].get('total_tokens', 0)
            
            return response_data
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к GigaChat API: {e}")
            raise Exception(f"Ошибка API: {e}")
    
    def _parse_response(self, response_text: str) -> Dict:
        """Парсит ответ от API и извлекает данные классификации"""
        try:
            # Пытаемся найти JSON в ответе
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON не найден в ответе")
            
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Валидируем данные
            required_fields = ['category_id', 'social_tension_index', 'spike_index', 'confidence']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Отсутствует поле {field}")
            
            # Нормализуем данные
            category_id = str(data['category_id'])
            if category_id not in self.categories:
                raise ValueError(f"Неизвестная категория: {category_id}")
            
            return {
                'category_id': category_id,
                'category_name': self.categories[category_id],
                'social_tension_index': max(0, min(100, int(data['social_tension_index']))),
                'spike_index': max(0, min(100, int(data['spike_index']))),
                'confidence': max(0.0, min(1.0, float(data['confidence']))),
                'reasoning': data.get('reasoning', 'Нет объяснения')
            }
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа: {e}")
            logger.error(f"Ответ API: {response_text}")
            raise ValueError(f"Не удалось распарсить ответ: {e}")
    
    def _fallback_classification(self, title: str, content: str) -> Dict:
        """Fallback классификация на основе ключевых слов"""
        logger.warning(f"Используется fallback классификация для: {title[:50]}...")
        
        text = f"{title} {content}".lower()
        
        # Простая классификация по ключевым словам
        if any(word in text for word in ['война', 'атака', 'удар', 'обстрел', 'военные', 'боевые']):
            category_id = '1'
            tension = 85
            spike = 75
        elif any(word in text for word in ['политика', 'решение', 'заявление', 'дипломатия', 'переговоры']):
            category_id = '2'
            tension = 60
            spike = 50
        elif any(word in text for word in ['экономика', 'санкции', 'торговля', 'финансы', 'рубль']):
            category_id = '3'
            tension = 70
            spike = 60
        elif any(word in text for word in ['жертвы', 'беженцы', 'гуманитарный', 'помощь', 'кризис']):
            category_id = '4'
            tension = 90
            spike = 80
        elif any(word in text for word in ['международный', 'поддержка', 'осуждение', 'оон', 'нато']):
            category_id = '5'
            tension = 65
            spike = 55
        elif any(word in text for word in ['кибер', 'хакер', 'информация', 'данные', 'безопасность']):
            category_id = '6'
            tension = 75
            spike = 65
        elif any(word in text for word in ['пропаганда', 'фейк', 'дезинформация', 'ложь', 'обман']):
            category_id = '7'
            tension = 80
            spike = 70
        else:
            category_id = '8'
            tension = 30
            spike = 20
        
        return {
            'category_id': category_id,
            'category_name': self.categories[category_id],
            'social_tension_index': tension,
            'spike_index': spike,
            'confidence': 0.3,
            'reasoning': 'Fallback классификация из-за ошибки API'
        }
    
    def classify(self, title: str, content: str) -> Dict:
        """
        Классифицирует новость
        
        Args:
            title: Заголовок новости
            content: Содержимое новости
            
        Returns:
            Dict: Результат классификации
        """
        self.stats['total_requests'] += 1
        
        # Проверяем кэш
        cache_key = self._get_cache_key(title, content)
        if cache_key in self.cache:
            self.stats['cached_requests'] += 1
            result = self.cache[cache_key].copy()
            result['cached'] = True
            logger.info(f"Результат получен из кэша для: {title[:50]}...")
            return result
        
        try:
            # Создаем промпт
            prompt = self._create_classification_prompt(title, content)
            
            # Отправляем запрос к API
            response = self._make_api_request(prompt)
            
            # Парсим ответ GigaChat
            if 'alternatives' in response and len(response['alternatives']) > 0:
                content = response['alternatives'][0]['message']['content']
            else:
                raise ValueError("Неожиданный формат ответа GigaChat")
            
            result = self._parse_response(content)
            result['cached'] = False
            
            # Сохраняем в кэш
            self.cache[cache_key] = result.copy()
            self.save_cache()
            
            logger.info(f"Новость классифицирована: {result['category_name']} (напряженность: {result['social_tension_index']})")
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Ошибка при классификации новости: {e}")
            
            # Используем fallback
            result = self._fallback_classification(title, content)
            result['cached'] = False
            return result
    
    def get_stats(self) -> Dict:
        """Возвращает статистику использования"""
        return self.stats.copy()
    
    def clear_cache(self):
        """Очищает кэш"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("Кэш очищен")
    
    def __del__(self):
        """Деструктор - сохраняет кэш при завершении"""
        try:
            self.save_cache()
        except:
            pass