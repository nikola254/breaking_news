#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-классификатор новостей на базе gen-api.ru с Long-Polling

Этот модуль содержит функции для:
- Классификации новостей по категориям с помощью gen-api.ru
- Расчет индексов социальной напряженности и всплеска
- Кэширование результатов для экономии токенов
- Long-Polling для получения результатов
"""

import os
import json
import logging
import hashlib
import requests
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)

class GenApiNewsClassifier:
    """AI-классификатор новостей на базе gen-api.ru с Long-Polling"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация классификатора
        
        Args:
            api_key: API ключ для gen-api.ru
        """
        self.api_key = api_key or os.environ.get('GEN_API_KEY')
        
        # Проверяем наличие API ключа
        if not self.api_key:
            logger.warning("Не найден API ключ gen-api.ru, будет использоваться только fallback классификация")
            self.api_key = None
        
        # Настройки для gen-api.ru
        self.api_url = "https://api.gen-api.ru/api/v1/networks/chat-gpt-3"
        self.status_url = "https://api.gen-api.ru/api/v1/requests"
        
        # Категории новостей (5 категорий)
        self.categories = {
            '1': 'military_operations',
            '2': 'humanitarian_crisis', 
            '3': 'economic_consequences',
            '4': 'political_decisions',
            '5': 'information_social'
        }
        
        # Кэш для результатов классификации
        self.cache = {}
        self.cache_file = "gen_api_classifier_cache.json"
        self.load_cache()
        
        # Статистика использования
        self.stats = {
            'total_requests': 0,
            'cached_requests': 0,
            'tokens_used': 0,
            'errors': 0,
            'api_requests': 0
        }
        
        logger.info("GenApiNewsClassifier инициализирован с gen-api.ru")
    
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
2. humanitarian_crisis - Гуманитарные кризисы, беженцы, жертвы
3. economic_consequences - Экономические последствия, санкции, торговля
4. political_decisions - Политические решения, заявления, дипломатия
5. information_social - Информационно-социальные аспекты

ИНДЕКСЫ (0-100):
- social_tension_index: Насколько новость может вызвать социальную напряженность
- spike_index: Насколько новость может вызвать всплеск обсуждений

Ответь ТОЛЬКО в формате JSON:
{{
  "category_id": "номер_категории",
  "category_name": "название_категории",
  "social_tension_index": число_от_0_до_100,
  "spike_index": число_от_0_до_100,
  "confidence": число_от_0_до_1
}}"""
        
        return prompt
    
    def _make_api_request(self, prompt: str) -> Dict:
        """
        Отправляет запрос к gen-api.ru и получает результат через Long-Polling
        
        Args:
            prompt: Промпт для отправки
            
        Returns:
            Dict: Ответ от API
        """
        if not self.api_key:
            raise Exception("API ключ gen-api.ru не настроен")
        
        try:
            # Создаем задачу на генерацию
            input_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "is_sync": False,      # Асинхронный режим для Long-Polling
                "max_tokens": 1000,
                "temperature": 0.3,
                "top_p": 0.95
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            logger.info("Отправляем запрос к gen-api.ru...")
            response = requests.post(self.api_url, json=input_data, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"API вернул статус {response.status_code}: {response.text}")
            
            task_data = response.json()
            request_id = task_data.get('request_id')
            
            if not request_id:
                raise Exception(f"Не получен request_id: {task_data}")
            
            logger.info(f"Задача создана, request_id: {request_id}")
            
            # Long-Polling для получения результата
            result = self._wait_for_result(request_id)
            
            # Подсчитываем токены (если есть информация о стоимости)
            if 'cost' in result:
                cost = result['cost']
                estimated_tokens = int(cost * 1000)  # Примерная оценка
                self.stats['tokens_used'] += estimated_tokens
            
            self.stats['api_requests'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к gen-api.ru: {e}")
            raise Exception(f"Ошибка API: {e}")
    
    def _wait_for_result(self, request_id: int, max_wait_time: int = 60) -> Dict:
        """
        Ожидает результат выполнения задачи через Long-Polling
        
        Args:
            request_id: ID запроса
            max_wait_time: Максимальное время ожидания в секундах
            
        Returns:
            Dict: Результат выполнения
        """
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # Правильный URL для проверки статуса согласно документации
        status_url = f"https://api.gen-api.ru/api/v1/request/get/{request_id}"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                logger.info(f"Проверяем статус задачи {request_id}...")
                response = requests.get(status_url, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    logger.warning(f"Ошибка при проверке статуса: {response.status_code}")
                    time.sleep(5)  # Ждем 5 секунд перед следующей проверкой
                    continue
                
                status_data = response.json()
                status = status_data.get('status')
                
                logger.info(f"Статус задачи {request_id}: {status}")
                
                if status == 'success':
                    logger.info("✅ Задача выполнена успешно!")
                    return status_data
                elif status == 'failed':
                    error_msg = status_data.get('error', 'Неизвестная ошибка')
                    raise Exception(f"Задача завершилась с ошибкой: {error_msg}")
                elif status in ['starting', 'processing']:
                    # Задача еще выполняется, ждем 5 секунд
                    logger.info("Задача в работе, ждем 5 секунд...")
                    time.sleep(5)
                    continue
                else:
                    logger.warning(f"Неизвестный статус: {status}")
                    time.sleep(5)
                    continue
                    
            except requests.RequestException as e:
                logger.warning(f"Ошибка при проверке статуса: {e}")
                time.sleep(5)
                continue
        
        raise Exception(f"Превышено время ожидания результата ({max_wait_time} сек)")
    
    def _parse_response(self, response_data: Dict) -> Dict:
        """Парсит ответ от API и извлекает данные классификации"""
        try:
            # Извлекаем ответ из result (формат Long-Polling)
            result = response_data.get('result', [])
            
            if result and len(result) > 0:
                # Берем первый элемент из массива result
                response_text = result[0]
            else:
                # Fallback для старого формата
                output = response_data.get('output', '')
                response_text = str(output)
            
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
                'confidence': max(0.0, min(1.0, float(data['confidence'])))
            }
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа: {e}")
            logger.error(f"Ответ API: {response_data}")
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
        elif any(word in text for word in ['жертвы', 'беженцы', 'гуманитарный', 'помощь', 'кризис']):
            category_id = '2'
            tension = 90
            spike = 80
        elif any(word in text for word in ['экономика', 'санкции', 'торговля', 'финансы', 'рубль']):
            category_id = '3'
            tension = 70
            spike = 60
        elif any(word in text for word in ['политика', 'решение', 'заявление', 'дипломатия', 'переговоры']):
            category_id = '4'
            tension = 60
            spike = 50
        else:
            category_id = '5'
            tension = 30
            spike = 20
        
        return {
            'category_id': category_id,
            'category_name': self.categories[category_id],
            'social_tension_index': tension,
            'spike_index': spike,
            'confidence': 0.3
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
            
            # Парсим ответ
            result = self._parse_response(response)
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
