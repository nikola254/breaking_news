#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки GigaChat API
"""

import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gigachat_auth(key_id, secret):
    """Тестирует аутентификацию в GigaChat"""
    try:
        auth_url = "https://auth.iam.sbercloud.ru/auth/system/openid/token"
        
        auth_data = {
            'grant_type': 'access_key',
            'client_id': key_id,
            'client_secret': secret
        }
        
        logger.info("Получаем токен доступа...")
        response = requests.post(auth_url, data=auth_data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access_token']
            logger.info("✅ Токен получен успешно")
            return access_token
        else:
            logger.error(f"❌ Ошибка аутентификации: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка при получении токена: {e}")
        return None

def test_gigachat_api(access_token, project_id):
    """Тестирует API запрос к GigaChat"""
    try:
        api_url = "https://gigachat.api.cloud.ru/api/gigachat/v1/chat/completions"
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": "Привет! Как дела?"
                }
            ],
            "model": "GigaChat",
            "options": {
                "temperature": 0.3,
                "top_p": 0.95,
                "max_tokens": 100,
                "repetition_penalty": 1.0,
                "max_alternatives": 1
            },
            "project_id": project_id
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        logger.info("Отправляем запрос к GigaChat API...")
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info("✅ API запрос успешен")
            
            if 'alternatives' in response_data and len(response_data['alternatives']) > 0:
                content = response_data['alternatives'][0]['message']['content']
                logger.info(f"Ответ GigaChat: {content}")
                return True
            else:
                logger.error("❌ Неожиданный формат ответа")
                return False
        else:
            logger.error(f"❌ Ошибка API: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при запросе к API: {e}")
        return False

def main():
    """Основная функция тестирования"""
    logger.info("=== Тестирование GigaChat API ===")
    
    # Используем реальные учетные данные
    key_id = 'a2512b4c794de9b61a5971a31a831ab2'
    secret = '328eba3d08e4b929a5eeddad3110e7f7'
    
    # Пробуем найти Project ID из переменных окружения или используем тестовый
    project_id = os.environ.get('GIGACHAT_PROJECT_ID', 'test_project_id')
    
    logger.info(f"Key ID: {key_id[:10]}...")
    logger.info(f"Project ID: {project_id}")
    
    # Тестируем аутентификацию
    access_token = test_gigachat_auth(key_id, secret)
    if not access_token:
        return
    
    # Тестируем API
    success = test_gigachat_api(access_token, project_id)
    
    if success:
        logger.info("🎉 Все тесты прошли успешно! GigaChat API готов к использованию.")
    else:
        logger.error("❌ Тесты не прошли. Проверьте настройки.")

if __name__ == "__main__":
    main()
